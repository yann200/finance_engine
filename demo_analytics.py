"""Read prices from market.db and print a performance and risk summary.

Run `demo_ingest.py` first so that the database contains data.
"""

from finance_engine.analytics import drawdown_series, summarize
from finance_engine.data.repository import PriceRepository
from finance_engine.logging_config import setup_logging

setup_logging(level="INFO")

with PriceRepository("market.db") as repo:
    closes = repo.get_prices("AAPL")["close"]

print(summarize(closes, risk_free_rate=0.03))
print("\nWorst drawdown date:", drawdown_series(closes).idxmin().date())