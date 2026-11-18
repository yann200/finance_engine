"""SQLite access layer.

``PriceRepository`` is the only place in the project that contains SQL.
The rest of the code reads and writes prices through its methods, so the
database engine can be replaced without touching the analytics.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from finance_engine.exceptions import InsufficientDataError, RepositoryError
from finance_engine.models.asset import Asset
from finance_engine.utils.decorators import timer

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    ticker   TEXT PRIMARY KEY,
    name     TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT 'USD'
);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT    NOT NULL REFERENCES assets(ticker),
    date   TEXT    NOT NULL,                 -- ISO format YYYY-MM-DD
    close  REAL    NOT NULL CHECK (close > 0),
    volume INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ticker, date)               -- forbids duplicates
);
"""

# Daily return computed by the database with a window function.
# The first row of each ticker has no previous close, hence NULL.
RETURNS_QUERY = """
SELECT date,
       close / LAG(close) OVER (ORDER BY date) - 1 AS daily_return
FROM prices
WHERE ticker = ?
ORDER BY date
"""


class PriceRepository:
    """Store and retrieve asset prices in a SQLite database.

    Can be used as a context manager so the connection is always closed::

        with PriceRepository("market.db") as repo:
            repo.save_prices(Asset("AAPL"), prices)

    Args:
        db_path: Path of the database file, or ``":memory:"`` (default) for a
            temporary database that disappears when the repository is closed.

    Raises:
        RepositoryError: If the database cannot be opened or initialised.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        try:
            if str(db_path) != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path))
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(SCHEMA)
        except (sqlite3.Error, OSError) as exc:
            raise RepositoryError(f"Cannot open database '{db_path}'") from exc

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> PriceRepository:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    # -- writing -------------------------------------------------------------

    @timer
    def save_prices(self, asset: Asset, prices: pd.DataFrame) -> int:
        """Insert or update the prices of ``asset``.

        The operation is idempotent: saving the same dates twice updates the
        existing rows instead of creating duplicates. It is also atomic: if one
        row is rejected, nothing is written.

        Args:
            asset: The asset the prices belong to.
            prices: Standard-format table (see ``providers.validate_prices``).

        Returns:
            The number of rows written.

        Raises:
            InsufficientDataError: If ``prices`` is empty.
            RepositoryError: If columns are missing or the database refuses the data.
        """
        if prices.empty:
            raise InsufficientDataError(f"No prices to save for {asset.ticker}")
        if not {"close", "volume"} <= set(prices.columns):
            raise RepositoryError("Prices must have 'close' and 'volume' columns")

        rows = [
            (asset.ticker, pd.Timestamp(day).strftime("%Y-%m-%d"), float(close), int(volume))
            for day, close, volume in zip(
                prices.index, prices["close"], prices["volume"]
            )
        ]

        try:
            with self._conn:  # one transaction: commit on success, rollback on error
                self._conn.execute(
                    "INSERT OR IGNORE INTO assets (ticker, name, currency) VALUES (?, ?, ?)",
                    (asset.ticker, asset.name, asset.currency),
                )
                self._conn.executemany(
                    "INSERT OR REPLACE INTO prices (ticker, date, close, volume) "
                    "VALUES (?, ?, ?, ?)",
                    rows,
                )
        except sqlite3.Error as exc:
            raise RepositoryError(f"Cannot save prices for {asset.ticker}") from exc

        logger.info("%d price(s) saved for %s", len(rows), asset.ticker)
        return len(rows)

    # -- reading -------------------------------------------------------------

    def _read(self, query: str, params: list) -> pd.DataFrame:
        """Run a SELECT and return the result indexed by its ``date`` column."""
        try:
            return pd.read_sql_query(
                query, self._conn, params=params, parse_dates=["date"], index_col="date"
            )
        except (sqlite3.Error, pd.errors.DatabaseError) as exc:
            raise RepositoryError("Database read failed") from exc

    def get_prices(
        self, ticker: str, start: str | None = None, end: str | None = None
    ) -> pd.DataFrame:
        """Return the stored prices of ``ticker``.

        Args:
            ticker: Market symbol (case-insensitive).
            start: Optional first date (inclusive), ``YYYY-MM-DD``.
            end: Optional last date (inclusive), ``YYYY-MM-DD``.

        Returns:
            DataFrame indexed by date with ``close`` and ``volume`` columns.

        Raises:
            InsufficientDataError: If nothing is stored for this ticker/period.
        """
        symbol = ticker.strip().upper()
        # Only fixed SQL fragments are concatenated; values always go through
        # '?' placeholders, which prevents SQL injection.
        query = "SELECT date, close, volume FROM prices WHERE ticker = ?"
        params: list = [symbol]
        if start:
            query += " AND date >= ?"
            params.append(str(start))
        if end:
            query += " AND date <= ?"
            params.append(str(end))
        query += " ORDER BY date"

        prices = self._read(query, params)
        if prices.empty:
            raise InsufficientDataError(f"No stored prices for {symbol}")
        return prices

    def get_daily_returns(self, ticker: str) -> pd.Series:
        """Return the daily returns of ``ticker``, computed in SQL with ``LAG``.

        Raises:
            InsufficientDataError: If fewer than 2 prices are stored.
        """
        symbol = ticker.strip().upper()
        frame = self._read(RETURNS_QUERY, [symbol])
        returns = frame["daily_return"].dropna()
        if len(frame) < 2 or returns.empty:
            raise InsufficientDataError(
                f"At least 2 stored prices are required to compute returns for {symbol}"
            )
        return returns

    def list_tickers(self) -> list[str]:
        """Return all tickers known to the database, sorted."""
        try:
            rows = self._conn.execute("SELECT ticker FROM assets ORDER BY ticker").fetchall()
        except sqlite3.Error as exc:
            raise RepositoryError("Cannot list tickers") from exc
        return [row[0] for row in rows]