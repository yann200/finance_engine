"""Momentum strategy."""

from __future__ import annotations

import numbers

import pandas as pd

from finance_engine.analytics.validation import clean_prices
from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.base import Strategy, require_positive_int


class MomentumStrategy(Strategy):
    """Be invested when the asset rose over the last ``lookback`` days.

    Momentum is the observation that assets which recently went up tend to
    keep going up over the short and medium term. The signal compares today's
    price with the price ``lookback`` days ago.

    Args:
        lookback: Number of days used to measure the past performance
            (default 126, about six months of trading).
        threshold: Minimum past return required to be invested, as a decimal
            (0.02 = +2 %). Default 0: any positive performance.

    Raises:
        InvalidStrategyError: If ``lookback`` is not a positive integer or
            ``threshold`` is not a number.
    """

    def __init__(self, lookback: int = 126, threshold: float = 0.0) -> None:
        self.lookback = require_positive_int(lookback, "lookback")
        if isinstance(threshold, bool) or not isinstance(threshold, numbers.Real):
            raise InvalidStrategyError(f"threshold must be a number, got {threshold!r}")
        self.threshold = float(threshold)

    def params(self) -> dict:
        return {"lookback": self.lookback, "threshold": self.threshold}

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        series = clean_prices(prices)
        past_return = series / series.shift(self.lookback) - 1
        # The first `lookback` values are NaN, so the comparison is False: cash.
        return (past_return > self.threshold).astype(int)