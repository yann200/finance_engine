"""Integration tests: provider -> validation -> repository -> SQL analytics.

These tests exercise several components together. They use a CSV provider and
a fake Yahoo downloader, so they run without any network access.
"""

import pandas as pd
import pytest

from finance_engine.data.providers import CsvProvider, YahooProvider
from finance_engine.data.repository import PriceRepository
from finance_engine.exceptions import InvalidTickerError
from finance_engine.models.asset import Asset

CSV_CONTENT = """Date,Open,High,Low,Close,Adj Close,Volume
2024-01-01,100,101,99,100.0,100.0,1000
2024-01-02,100,111,99,110.0,110.0,1100
2024-01-03,110,112,98,99.0,99.0,900
2024-01-04,99,100,97,99.0,99.0,950
"""


@pytest.fixture
def csv_dir(tmp_path):
    (tmp_path / "AAPL.csv").write_text(CSV_CONTENT)
    return tmp_path


def test_csv_to_database_to_returns(csv_dir, tmp_path):
    provider = CsvProvider(csv_dir)

    with PriceRepository(tmp_path / "market.db") as repo:
        prices = provider.fetch("aapl")
        repo.save_prices(Asset("aapl"), prices)

        sql_returns = repo.get_daily_returns("AAPL")

    expected = prices["close"].pct_change().dropna()
    assert sql_returns.tolist() == pytest.approx(expected.tolist())


def test_running_the_pipeline_twice_creates_no_duplicates(csv_dir):
    provider = CsvProvider(csv_dir)

    with PriceRepository() as repo:
        for _ in range(2):
            repo.save_prices(Asset("AAPL"), provider.fetch("AAPL"))

        assert len(repo.get_prices("AAPL")) == 4


def test_unknown_ticker_stops_the_pipeline_before_the_database(csv_dir):
    with PriceRepository() as repo:
        with pytest.raises(InvalidTickerError):
            repo.save_prices(Asset("MSFT"), CsvProvider(csv_dir).fetch("MSFT"))

        assert repo.list_tickers() == []  # nothing was written


def test_yahoo_pipeline_with_fake_downloader():
    index = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"])
    fake = pd.DataFrame(
        {("Close", "AAPL"): [10.0, 11.0, 12.1], ("Volume", "AAPL"): [1, 2, 3]},
        index=index,
    )
    provider = YahooProvider(downloader=lambda *args, **kwargs: fake)

    with PriceRepository() as repo:
        repo.save_prices(Asset("AAPL", name="Apple"), provider.fetch("AAPL"))
        returns = repo.get_daily_returns("AAPL")

    assert returns.tolist() == pytest.approx([0.1, 0.1])