"""Buy-and-hold strategy, the reference every other strategy must beat."""

from __future__ import annotations

import pandas as pd

from finance_engine.analytics.validation import clean_prices
from finance_engine.strategies.base import Strategy


class BuyAndHoldStrategy(Strategy):
    """Always invested. Serves as the baseline for comparisons.

    Because of the one-day shift applied by ``positions``, the first day is
    spent in cash and the asset is held from the second day onwards.
    """

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        series = clean_prices(prices)
        return pd.Series(1, index=series.index)