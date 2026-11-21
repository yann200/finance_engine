"""Return and performance calculations.

A *return* is the relative change of a price between two dates:
``price_t / price_(t-1) - 1``. Returns are expressed as decimals
(0.01 = +1 %).
"""

from __future__ import annotations

import pandas as pd

from finance_engine.analytics.validation import (
    check_periods,
    clean_prices,
    clean_series,
)

# Number of trading days in a year, the usual convention for daily data.
TRADING_DAYS_PER_YEAR = 252


def daily_returns(prices) -> pd.Series:
    """Compute the simple return of each period from a price series.

    Args:
        prices: Prices in chronological order.

    Returns:
        Returns, one fewer than the number of prices (the first price has no
        previous price). The index of ``prices`` is preserved.

    Raises:
        InsufficientDataError: If fewer than 2 prices are given.
        ValueError: If a price is not strictly positive.
    """
    return clean_prices(prices).pct_change().dropna()


def cumulative_return(returns) -> float:
    """Total return over the whole period, from a series of period returns.

    Returns are compounded: ``(1 + r1) * (1 + r2) * ... - 1``.

    Example:
        +10 % then -10 % gives -1 %, not 0 %.

    Raises:
        InsufficientDataError: If ``returns`` is empty.
    """
    series = clean_series(returns, minimum=1, what="returns")
    return float((1 + series).prod() - 1)


def equity_curve(returns, initial_value: float = 1.0) -> pd.Series:
    """Value of an investment over time, compounding the returns.

    Args:
        returns: Period returns in chronological order.
        initial_value: Amount invested at the start.

    Returns:
        The value after each period (same index as ``returns``).
    """
    series = clean_series(returns, minimum=1, what="returns")
    return initial_value * (1 + series).cumprod()


def annualized_return(
    returns, periods_per_year: float = TRADING_DAYS_PER_YEAR
) -> float:
    """Compound annual growth rate (CAGR) implied by the period returns.

    Formula: ``(1 + total_return) ** (periods_per_year / n_periods) - 1``.

    Args:
        returns: Period returns.
        periods_per_year: 252 for daily data, 12 for monthly, 1 for yearly.

    Raises:
        InsufficientDataError: If ``returns`` is empty.
        ValueError: If ``periods_per_year`` is not positive.
    """
    check_periods(periods_per_year)
    series = clean_series(returns, minimum=1, what="returns")
    total = cumulative_return(series)
    return float((1 + total) ** (periods_per_year / len(series)) - 1)