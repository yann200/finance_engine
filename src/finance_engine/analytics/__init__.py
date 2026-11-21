"""Analytics: returns, risk metrics and performance summary.

The most useful functions are re-exported here so users can write
``from finance_engine.analytics import max_drawdown``.
"""

from finance_engine.analytics.returns import (
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    cumulative_return,
    daily_returns,
    equity_curve,
)
from finance_engine.analytics.risk import (
    correlation_matrix,
    drawdown_series,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
    volatility,
)
from finance_engine.analytics.summary import PerformanceSummary, summarize

__all__ = [
    "TRADING_DAYS_PER_YEAR",
    "PerformanceSummary",
    "annualized_return",
    "correlation_matrix",
    "cumulative_return",
    "daily_returns",
    "drawdown_series",
    "equity_curve",
    "max_drawdown",
    "sharpe_ratio",
    "summarize",
    "value_at_risk",
    "volatility",
]