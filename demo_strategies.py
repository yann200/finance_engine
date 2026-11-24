"""Compare the strategies on the prices stored in market.db (before costs).

Run `demo_ingest.py` first so that the database contains data.
"""

import pandas as pd

from finance_engine.analytics import (
    annualized_return,
    cumulative_return,
    equity_curve,
    max_drawdown,
    sharpe_ratio,
    volatility,
)
from finance_engine.data.repository import PriceRepository
from finance_engine.logging_config import setup_logging
from finance_engine.strategies import create_strategy

TICKER = "AAPL"

setup_logging(level="WARNING")  # keep the output readable

with PriceRepository("market.db") as repo:
    closes = repo.get_prices(TICKER)["close"]

strategies = [
    create_strategy("buy_and_hold"),
    create_strategy("moving_average", short_window=20, long_window=100),
    create_strategy("momentum", lookback=60),
]

rows = {}
for strategy in strategies:
    returns = strategy.gross_returns(closes)
    curve = equity_curve(returns, initial_value=1.0)
    rows[strategy.name] = {
        "total return": cumulative_return(returns),
        "annualized": annualized_return(returns),
        "volatility": volatility(returns),
        "sharpe": sharpe_ratio(returns),
        "max drawdown": max_drawdown([1.0, *curve]),
        "days invested": f"{int(strategy.positions(closes).sum())}/{len(closes)}",
    }

table = pd.DataFrame(rows).T
print(f"\n{TICKER} - strategies compared (gross of transaction costs)\n")
percent = lambda x: f"{x:.2%}"
print(
    table.to_string(
        formatters={
            "total return": percent,
            "annualized": percent,
            "volatility": percent,
            "max drawdown": percent,
            "sharpe": lambda x: f"{x:.2f}",
        }
    )
)