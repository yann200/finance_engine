"""Market data providers.

A provider knows how to *obtain* prices from an external source and always
returns them in the same standard format:

* index: ``DatetimeIndex`` named ``date`` (sorted, unique, timezone-naive)
* columns: ``close`` (float, > 0) and ``volume`` (int)

Providers never touch the database; storing prices is the job of
``PriceRepository``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

import pandas as pd

from finance_engine.exceptions import DataProviderError, InvalidTickerError
from finance_engine.utils.decorators import retry, timer

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("close", "volume")


def validate_prices(prices: pd.DataFrame | None, ticker: str) -> pd.DataFrame:
    """Check raw price data and return it in the standard format.

    External data is never trusted: this function is the single gate that
    every provider must go through.

    Checks and fixes performed:
        * empty data -> ``InvalidTickerError``
        * missing ``close`` / ``volume`` column -> ``DataProviderError``
        * rows without a close price are dropped (warning logged)
        * non-positive close prices -> ``DataProviderError``
        * duplicated dates are dropped, keeping the last one (warning logged)
        * missing volumes become 0
        * dates are normalised (no time, no timezone) and sorted

    Args:
        prices: Raw table, indexed by date. Column names are case-insensitive.
        ticker: Symbol used in error and log messages.

    Returns:
        A new, clean DataFrame in the standard format.
    """
    if prices is None or prices.empty:
        raise InvalidTickerError(f"No data returned for ticker '{ticker}'")

    cleaned = prices.copy()
    cleaned.columns = [str(col).strip().lower() for col in cleaned.columns]

    missing = [col for col in REQUIRED_COLUMNS if col not in cleaned.columns]
    if missing:
        raise DataProviderError(f"Missing columns for '{ticker}': {missing}")
    cleaned = cleaned[list(REQUIRED_COLUMNS)].copy()

    try:
        index = pd.DatetimeIndex(pd.to_datetime(cleaned.index))
    except (ValueError, TypeError) as exc:
        raise DataProviderError(f"Invalid dates for '{ticker}'") from exc
    if index.tz is not None:
        index = index.tz_localize(None)
    cleaned.index = index.normalize().rename("date")

    cleaned["close"] = pd.to_numeric(cleaned["close"], errors="coerce")
    rows_before = len(cleaned)
    cleaned = cleaned.dropna(subset=["close"])
    if len(cleaned) < rows_before:
        logger.warning(
            "%d row(s) without close price dropped for %s",
            rows_before - len(cleaned), ticker,
        )
    if cleaned.empty:
        raise InvalidTickerError(f"No usable prices for ticker '{ticker}'")

    if (cleaned["close"] <= 0).any():
        raise DataProviderError(f"Non-positive close price found for '{ticker}'")

    duplicated = cleaned.index.duplicated(keep="last")
    if duplicated.any():
        logger.warning(
            "%d duplicated date(s) dropped for %s", int(duplicated.sum()), ticker
        )
        cleaned = cleaned[~duplicated]

    volume = pd.to_numeric(cleaned["volume"], errors="coerce").fillna(0)
    cleaned["volume"] = volume.astype("int64")

    return cleaned.sort_index()


def _slice_dates(
    prices: pd.DataFrame, start: str | None, end: str | None
) -> pd.DataFrame:
    """Keep only the rows between ``start`` and ``end`` (both inclusive)."""
    if start:
        prices = prices.loc[prices.index >= pd.Timestamp(start)]
    if end:
        prices = prices.loc[prices.index <= pd.Timestamp(end)]
    return prices


class PriceProvider(ABC):
    """Interface every price source must implement."""

    @abstractmethod
    def fetch(
        self, ticker: str, start: str | None = None, end: str | None = None
    ) -> pd.DataFrame:
        """Return validated prices for ``ticker`` in the standard format.

        Args:
            ticker: Market symbol (case-insensitive).
            start: Optional first date, ISO format ``YYYY-MM-DD``.
            end: Optional last date, ISO format ``YYYY-MM-DD``.

        Raises:
            InvalidTickerError: Unknown ticker or no data.
            DataProviderError: Any other retrieval or format problem.
        """


class CsvProvider(PriceProvider):
    """Read prices from ``<directory>/<TICKER>.csv`` files.

    The expected layout is the one of Yahoo Finance exports: the first column
    holds the date, and the file has ``Close`` and ``Volume`` columns.
    This provider needs no network, which makes it ideal for tests.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def fetch(
        self, ticker: str, start: str | None = None, end: str | None = None
    ) -> pd.DataFrame:
        symbol = ticker.strip().upper()
        path = self.directory / f"{symbol}.csv"
        if not path.is_file():
            raise InvalidTickerError(f"No CSV file for '{symbol}' at {path}")

        try:
            raw = pd.read_csv(path, index_col=0)  # first column = date
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            raise DataProviderError(f"Cannot read {path}") from exc

        prices = validate_prices(raw, symbol)
        return _slice_dates(prices, start, end)


Downloader = Callable[..., pd.DataFrame]


class YahooProvider(PriceProvider):
    """Download prices from Yahoo Finance through ``yfinance``.

    Network failures are retried automatically. An unknown ticker is *not*
    retried (see ``retry``).

    Args:
        downloader: Function with the signature of ``yfinance.download``.
            Defaults to the real one; tests inject a fake to avoid the network.
    """

    def __init__(self, downloader: Downloader | None = None) -> None:
        self._downloader = downloader

    def _get_downloader(self) -> Downloader:
        """Return the injected downloader, or import ``yfinance`` lazily."""
        if self._downloader is not None:
            return self._downloader
        try:
            import yfinance as yf
        except ImportError as exc:
            raise DataProviderError("The 'yfinance' package is not installed") from exc
        return yf.download

    @timer
    @retry(attempts=3, delay=1.0, backoff=2.0)
    def fetch(
        self, ticker: str, start: str | None = None, end: str | None = None
    ) -> pd.DataFrame:
        symbol = ticker.strip().upper()
        download = self._get_downloader()

        logger.info("Downloading %s from Yahoo Finance", symbol)
        try:
            # auto_adjust=True: 'Close' is corrected for splits and dividends.
            raw = download(
                symbol, start=start, end=end, auto_adjust=True, progress=False
            )
        except Exception as exc:  # the library may raise anything
            raise DataProviderError(f"Download failed for '{symbol}'") from exc

        if raw is None:
            raw = pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            # Recent yfinance versions return (field, ticker) column pairs.
            raw.columns = raw.columns.get_level_values(0)

        return validate_prices(raw, symbol)