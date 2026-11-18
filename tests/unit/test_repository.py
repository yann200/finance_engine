"""Unit tests for PriceRepository (SQLite in memory unless stated)."""

import pandas as pd
import pytest

from finance_engine.data.repository import PriceRepository
from finance_engine.exceptions import InsufficientDataError, RepositoryError
from finance_engine.models.asset import Asset


@pytest.fixture
def repo():
    with PriceRepository(":memory:") as repository:
        yield repository


def test_save_then_get_roundtrip(repo, sample_prices):
    saved = repo.save_prices(Asset("AAPL"), sample_prices)

    stored = repo.get_prices("AAPL")

    assert saved == 4
    assert stored["close"].tolist() == [100.0, 110.0, 99.0, 99.0]
    assert stored["volume"].tolist() == [1000, 1100, 900, 950]
    assert stored.index[0] == pd.Timestamp("2024-01-01")


def test_save_is_idempotent(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)
    repo.save_prices(Asset("AAPL"), sample_prices)

    assert len(repo.get_prices("AAPL")) == 4  # no duplicates


def test_save_updates_existing_dates(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)
    corrected = sample_prices.copy()
    corrected.loc["2024-01-01", "close"] = 105.0

    repo.save_prices(Asset("AAPL"), corrected)

    assert repo.get_prices("AAPL")["close"].iloc[0] == 105.0


def test_get_prices_filters_by_date(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)

    stored = repo.get_prices("AAPL", start="2024-01-02", end="2024-01-03")

    assert stored["close"].tolist() == [110.0, 99.0]


def test_get_prices_is_case_insensitive(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)
    assert len(repo.get_prices("aapl")) == 4


def test_get_prices_unknown_ticker_raises(repo):
    with pytest.raises(InsufficientDataError):
        repo.get_prices("MSFT")


def test_prices_of_different_tickers_are_separated(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)
    repo.save_prices(Asset("MSFT"), sample_prices.head(2))

    assert len(repo.get_prices("AAPL")) == 4
    assert len(repo.get_prices("MSFT")) == 2
    assert repo.list_tickers() == ["AAPL", "MSFT"]


def test_daily_returns_computed_in_sql(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)

    returns = repo.get_daily_returns("AAPL")

    assert returns.tolist() == pytest.approx([0.1, -0.1, 0.0])
    assert returns.index[0] == pd.Timestamp("2024-01-02")  # first day has no return


def test_daily_returns_match_pandas(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices)

    sql_returns = repo.get_daily_returns("AAPL")
    pandas_returns = sample_prices["close"].pct_change().dropna()

    assert sql_returns.tolist() == pytest.approx(pandas_returns.tolist())


def test_daily_returns_need_two_prices(repo, sample_prices):
    repo.save_prices(Asset("AAPL"), sample_prices.head(1))
    with pytest.raises(InsufficientDataError):
        repo.get_daily_returns("AAPL")


def test_save_empty_prices_raises(repo, sample_prices):
    with pytest.raises(InsufficientDataError):
        repo.save_prices(Asset("AAPL"), sample_prices.head(0))


def test_save_without_required_columns_raises(repo, sample_prices):
    with pytest.raises(RepositoryError):
        repo.save_prices(Asset("AAPL"), sample_prices[["close"]])


def test_invalid_price_is_rejected_and_nothing_is_written(repo, sample_prices):
    bad = sample_prices.copy()
    bad.loc["2024-01-03", "close"] = -1.0  # violates CHECK (close > 0)

    with pytest.raises(RepositoryError):
        repo.save_prices(Asset("AAPL"), bad)

    with pytest.raises(InsufficientDataError):  # transaction rolled back
        repo.get_prices("AAPL")


def test_data_persists_on_disk(tmp_path, sample_prices):
    db_file = tmp_path / "data" / "market.db"  # parent folder created automatically

    with PriceRepository(db_file) as repo:
        repo.save_prices(Asset("AAPL"), sample_prices)
    with PriceRepository(db_file) as reopened:
        assert len(reopened.get_prices("AAPL")) == 4