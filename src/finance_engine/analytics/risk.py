"""Risk metrics: volatility, Sharpe ratio, drawdown, Value at Risk, correlation."""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from finance_engine.analytics.returns import TRADING_DAYS_PER_YEAR
from finance_engine.analytics.validation import (
    check_periods,
    clean_prices,
    clean_series,
)
from finance_engine.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


def volatility(returns, periods_per_year: float = TRADING_DAYS_PER_YEAR) -> float:
    """Annualised volatility: sample standard deviation of returns.

    Formula: ``std(returns) * sqrt(periods_per_year)``. Pass
    ``periods_per_year=1`` to get the raw, non-annualised value.

    Raises:
        InsufficientDataError: If fewer than 2 returns are given.
        ValueError: If ``periods_per_year`` is not positive.
    """
    check_periods(periods_per_year)
    series = clean_series(returns, minimum=2, what="returns")
    return float(series.std(ddof=1) * math.sqrt(periods_per_year))


def sharpe_ratio(
    returns,
    risk_free_rate: float = 0.0,
    periods_per_year: float = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualised Sharpe ratio: excess return per unit of risk.

    Formula: ``mean(excess) / std(excess) * sqrt(periods_per_year)``, where
    ``excess = return - risk_free_rate / periods_per_year``.

    Args:
        returns: Period returns.
        risk_free_rate: Annual risk-free rate as a decimal (0.03 = 3 %).
        periods_per_year: 252 for daily data.

    Returns:
        The ratio, or ``nan`` if returns never vary (the ratio is undefined
        when the risk is zero).

    Raises:
        InsufficientDataError: If fewer than 2 returns are given.
    """
    check_periods(periods_per_year)
    series = clean_series(returns, minimum=2, what="returns")
    excess = series - risk_free_rate / periods_per_year
    std = excess.std(ddof=1)
    if math.isclose(std, 0.0, abs_tol=1e-12):
        logger.warning("Sharpe ratio undefined: returns have zero variance")
        return float("nan")
    return float(excess.mean() / std * math.sqrt(periods_per_year))


def drawdown_series(prices) -> pd.Series:
    """Drop from the highest price reached so far, at each date.

    Formula: ``price / running_maximum - 1``. Always <= 0; 0 means the price
    is at a new high.

    Raises:
        InsufficientDataError: If fewer than 2 prices are given.
        ValueError: If a price is not strictly positive.
    """
    series = clean_prices(prices)
    return series / series.cummax() - 1


def max_drawdown(prices) -> float:
    """Worst peak-to-trough drop over the period (a negative number).

    Example:
        -0.35 means that at some point the investment was 35 % below its
        previous peak.
    """
    return float(drawdown_series(prices).min())


def value_at_risk(returns, confidence: float = 0.95) -> float:
    """Historical Value at Risk (VaR) of one period.

    The VaR is the return that is not expected to be worsened with the given
    confidence. It is computed directly from past returns (percentile), with
    no assumption about their distribution.

    Example:
        A 95 % VaR of -0.02 means that, historically, the loss exceeded 2 %
        on only 5 % of the periods.

    Args:
        returns: Period returns.
        confidence: Confidence level strictly between 0 and 1.

    Returns:
        The return threshold (negative when it is a loss).

    Raises:
        ValueError: If ``confidence`` is not strictly between 0 and 1.
        InsufficientDataError: If ``returns`` is empty.
    """
    if not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1")
    series = clean_series(returns, minimum=1, what="returns")
    return float(np.percentile(series, (1 - confidence) * 100))


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pairwise correlation of asset returns (one column per asset).

    Values range from -1 (opposite moves) to +1 (identical moves). Rows
    containing a missing value are ignored.

    Raises:
        TypeError: If ``returns`` is not a DataFrame.
        InsufficientDataError: If there are fewer than 2 assets or 2 dates.
    """
    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a DataFrame with one column per asset")
    if returns.shape[1] < 2:
        raise InsufficientDataError("At least 2 assets required for a correlation")
    complete = returns.dropna()
    if len(complete) < 2:
        raise InsufficientDataError(
            f"At least 2 common dates required, got {len(complete)}"
        )
    return complete.corr()