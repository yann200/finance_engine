"""Moving-average crossover strategy."""

from __future__ import annotations

import logging

import pandas as pd

from finance_engine.analytics.validation import clean_prices
from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.base import Strategy, require_positive_int

logger = logging.getLogger(__name__)


class MovingAverageStrategy(Strategy):
    """Be invested while the short moving average is above the long one.

    A moving average smooths prices over the last N days. When the short
    average rises above the long one, the recent trend is stronger than the
    long-term one: that is the buy signal. The opposite crossing means cash.

    Args:
        short_window: Days in the short average (default 50).
        long_window: Days in the long average (default 200).

    Raises:
        InvalidStrategyError: If a window is not a positive integer, or if
            ``short_window`` is not strictly smaller than ``long_window``.
    """

    def __init__(self, short_window: int = 50, long_window: int = 200) -> None:
        self.short_window = require_positive_int(short_window, "short_window")
        self.long_window = require_positive_int(long_window, "long_window")
        if self.short_window >= self.long_window:
            raise InvalidStrategyError(
                "short_window must be smaller than long_window "
                f"(got {self.short_window} and {self.long_window})"
            )

    def params(self) -> dict:
        return {"short_window": self.short_window, "long_window": self.long_window}

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        series = clean_prices(prices)
        if len(series) < self.long_window:
            logger.warning(
                "%d prices but a long window of %d: no signal can be generated",
                len(series), self.long_window,
            )
        short_average = series.rolling(self.short_window).mean()
        long_average = series.rolling(self.long_window).mean()
        # While an average is still undefined (NaN), the comparison is False,
        # so the strategy stays in cash during the warm-up period.
        return (short_average > long_average).astype(int)