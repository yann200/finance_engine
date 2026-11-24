"""Unit tests for the Strategy base class."""

import pandas as pd
import pytest

from finance_engine.analytics.validation import clean_prices
from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.base import Strategy, require_positive_int


class AlwaysLong(Strategy):
    def generate_signals(self, prices):
        return pd.Series(1, index=clean_prices(prices).index)


class InvalidSignals(Strategy):
    def generate_signals(self, prices):
        return pd.Series(2, index=clean_prices(prices).index)  # neither 0 nor 1


def test_strategy_is_abstract():
    with pytest.raises(TypeError):
        Strategy()


def test_name_defaults_to_class_name_and_repr_is_readable():
    strategy = AlwaysLong()
    assert strategy.name == "AlwaysLong"
    assert repr(strategy) == "AlwaysLong()"


def test_positions_are_signals_shifted_by_one_day():
    prices = [100.0, 101.0, 102.0, 103.0]
    strategy = AlwaysLong()

    positions = strategy.positions(prices)

    assert positions.tolist() == [0, 1, 1, 1]  # no position on the first day
    assert positions.iloc[1:].tolist() == strategy.generate_signals(prices).iloc[:-1].tolist()


def test_positions_reject_signals_other_than_0_or_1():
    with pytest.raises(InvalidStrategyError):
        InvalidSignals().positions([100.0, 101.0, 102.0])


def test_gross_returns_apply_the_position_to_the_asset_return():
    # position [0, 1, 1]; asset returns [nan, +10 %, -10 %]
    returns = AlwaysLong().gross_returns([100.0, 110.0, 99.0])
    assert returns.tolist() == pytest.approx([0.1, -0.1])


@pytest.mark.parametrize("value", [3, 1])
def test_require_positive_int_accepts_integers(value):
    assert require_positive_int(value, "x") == value


@pytest.mark.parametrize("value", [0, -2, 2.5, "3", True, None])
def test_require_positive_int_rejects_everything_else(value):
    with pytest.raises(InvalidStrategyError):
        require_positive_int(value, "x")