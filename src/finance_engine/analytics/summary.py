"""One-call performance and risk summary of a price series."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from finance_engine.analytics.returns import (
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    cumulative_return,
    daily_returns,
)
from finance_engine.analytics.risk import (
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
    volatility,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PerformanceSummary:
    """Key figures describing the performance and risk of an investment.

    All ratios are decimals (0.05 = 5 %), except ``sharpe_ratio`` and
    ``n_observations``.
    """

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    n_observations: int

    def as_dict(self) -> dict:
        """Return the summary as a plain dictionary (handy for CSV or JSON)."""
        return asdict(self)

    def __str__(self) -> str:
        return "\n".join(
            [
                f"Observations      : {self.n_observations}",
                f"Total return      : {self.total_return:.2%}",
                f"Annualized return : {self.annualized_return:.2%}",
                f"Volatility (ann.) : {self.volatility:.2%}",
                f"Sharpe ratio      : {self.sharpe_ratio:.2f}",
                f"Max drawdown      : {self.max_drawdown:.2%}",
                f"VaR 95% (1 day)   : {self.var_95:.2%}",
            ]
        )


def summarize(
    prices,
    risk_free_rate: float = 0.0,
    periods_per_year: float = TRADING_DAYS_PER_YEAR,
) -> PerformanceSummary:
    """Compute the main performance and risk metrics from a price series.

    Args:
        prices: Prices in chronological order (at least 3 values).
        risk_free_rate: Annual risk-free rate used for the Sharpe ratio.
        periods_per_year: 252 for daily prices.

    Raises:
        InsufficientDataError: If there are not enough prices.
    """
    returns = daily_returns(prices)
    summary = PerformanceSummary(
        total_return=cumulative_return(returns),
        annualized_return=annualized_return(returns, periods_per_year),
        volatility=volatility(returns, periods_per_year),
        sharpe_ratio=sharpe_ratio(returns, risk_free_rate, periods_per_year),
        max_drawdown=max_drawdown(prices),
        var_95=value_at_risk(returns, confidence=0.95),
        n_observations=len(returns),
    )
    logger.info("Summary computed over %d returns", summary.n_observations)
    return summary