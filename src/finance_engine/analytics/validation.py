"""Input checks shared by the analytics functions.

Analytics functions accept any sequence of numbers (list, NumPy array,
pandas Series). These helpers turn the input into a clean float Series and
raise the project's exceptions when it cannot be used.
"""

from __future__ import annotations

import pandas as pd

from finance_engine.exceptions import InsufficientDataError


def clean_series(data, minimum: int, what: str) -> pd.Series:
    """Convert ``data`` to a float Series, drop NaN, and check its length.

    Args:
        data: Sequence of numbers.
        minimum: Minimum number of valid (non-NaN) values required.
        what: Plural noun used in the error message (``"prices"``, ``"returns"``).

    Raises:
        InsufficientDataError: If fewer than ``minimum`` valid values remain.
    """
    series = pd.Series(data, dtype="float64").dropna()
    if len(series) < minimum:
        raise InsufficientDataError(
            f"At least {minimum} {what} required, got {len(series)}"
        )
    return series


def clean_prices(data) -> pd.Series:
    """Return a clean price Series (at least 2 values, all strictly positive).

    Raises:
        InsufficientDataError: If fewer than 2 prices are given.
        ValueError: If a price is zero or negative (programming error: prices
            coming from a provider are already validated).
    """
    prices = clean_series(data, minimum=2, what="prices")
    if (prices <= 0).any():
        raise ValueError("Prices must be strictly positive")
    return prices


def check_periods(periods_per_year: float) -> None:
    """Raise ``ValueError`` if ``periods_per_year`` is not positive."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")