"""Integration test: CSV -> validation -> SQLite -> pandas analytics."""

import pytest

from finance_engine.analytics import daily_returns, max_drawdown, summarize
from finance_engine.data.providers import CsvProvider
from finance_engine.data.repository import PriceRepository
from finance_engine.models.asset import Asset

CSV_CONTENT = """Date,Open,High,Low,Close,Adj Close,Volume
2024-01-01,100,101,99,100.0,100.0,1000
2024-01-02,100,111,99,110.0,110.0,1100
2024-01-03,110,112,98,99.0,99.0,900
2024-01-04,99,100,97,99.0,99.0,950
"""


@pytest.fixture
def stored_closes(tmp_path):
    """Run the ingestion and return what the database holds."""
    (tmp_path / "AAPL.csv").write_text(CSV_CONTENT)
    with PriceRepository(tmp_path / "market.db") as repo:
        repo.save_prices(Asset("AAPL"), CsvProvider(tmp_path).fetch("AAPL"))
        closes = repo.get_prices("AAPL")["close"]
        sql_returns = repo.get_daily_returns("AAPL")
    return closes, sql_returns


def test_sql_and_pandas_returns_agree(stored_closes):
    closes, sql_returns = stored_closes
    assert daily_returns(closes).tolist() == pytest.approx(sql_returns.tolist())


def test_summary_from_stored_prices(stored_closes):
    closes, _ = stored_closes

    summary = summarize(closes)

    assert summary.total_return == pytest.approx(-0.01)
    assert summary.max_drawdown == pytest.approx(-0.10)
    assert max_drawdown(closes) == pytest.approx(summary.max_drawdown)