"""Strategy interface shared by every trading strategy.

Conventions
-----------
* A strategy is **long-only**: a signal is ``1`` (invested) or ``0`` (in cash).
  Short selling is out of scope.
* ``generate_signals`` returns the decision taken **at the close of day t**,
  using prices up to and including day t.
* ``positions`` shifts the signals by one day: the decision of day t is only
  applied on day t+1. This is what prevents *look-ahead bias* (acting on
  information that was not yet known), and it is enforced here, once, for all
  strategies, so subclasses cannot get it wrong.
"""

from __future__ import annotations

import logging
import numbers
from abc import ABC, abstractmethod

import pandas as pd

from finance_engine.analytics.validation import clean_prices
from finance_engine.exceptions import InvalidStrategyError

logger = logging.getLogger(__name__)


def require_positive_int(value, name: str) -> int:
    """Return ``value`` as an ``int`` if it is a positive integer.

    Raises:
        InvalidStrategyError: If ``value`` is a bool, a float, or lower than 1.
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < 1:
        raise InvalidStrategyError(f"{name} must be a positive integer, got {value!r}")
    return int(value)


class Strategy(ABC):
    """Abstract base class of all strategies.

    Subclasses implement ``generate_signals`` (and usually ``params``); the
    shifting and return computation are inherited.
    """

    @property
    def name(self) -> str:
        """Human-readable name, the class name by default."""
        return type(self).__name__

    def params(self) -> dict:
        """Parameters of the strategy, used in ``repr`` and in reports."""
        return {}

    @abstractmethod
    def generate_signals(self, prices: pd.Series) -> pd.Series:
        """Return the daily signal: 1 = be invested, 0 = stay in cash.

        The signal at date t may only use prices up to date t.

        Args:
            prices: Closing prices in chronological order.

        Returns:
            An integer Series with the same index as the cleaned prices.
        """

    def positions(self, prices: pd.Series) -> pd.Series:
        """Return the position actually held each day (signals shifted by 1 day).

        The first day has no earlier signal, so the position is 0.

        Raises:
            InvalidStrategyError: If the strategy produced values other than 0 or 1.
        """
        signals = self.generate_signals(prices)
        if not signals.isin([0, 1]).all():
            raise InvalidStrategyError(
                f"{self.name} must produce signals equal to 0 or 1 only"
            )
        return signals.shift(1).fillna(0).astype(int)

    def gross_returns(self, prices: pd.Series) -> pd.Series:
        """Daily returns of the strategy **before transaction costs**.

        Formula: ``position(t) * asset_return(t)``. Costs and capital are
        handled by the backtester.
        """
        series = clean_prices(prices)
        asset_returns = series.pct_change()
        return (self.positions(series) * asset_returns).dropna()

    def __repr__(self) -> str:
        args = ", ".join(f"{key}={value!r}" for key, value in self.params().items())
        return f"{self.name}({args})"