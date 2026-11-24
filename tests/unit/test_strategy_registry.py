"""Unit tests for the strategy registry, and the no look-ahead property."""

import numpy as np
import pandas as pd
import pytest

from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies import (
    BuyAndHoldStrategy,
    MomentumStrategy,
    MovingAverageStrategy,
    available_strategies,
    create_strategy,
)


def test_available_strategies_are_sorted():
    assert available_strategies() == ["buy_and_hold", "momentum", "moving_average"]


def test_create_strategy_with_parameters():
    strategy = create_strategy("moving_average", short_window=5, long_window=20)

    assert isinstance(strategy, MovingAverageStrategy)
    assert strategy.params() == {"short_window": 5, "long_window": 20}


def test_create_strategy_ignores_case_and_spaces():
    assert isinstance(create_strategy("  Momentum "), MomentumStrategy)


def test_create_strategy_without_parameters_uses_defaults():
    assert isinstance(create_strategy("buy_and_hold"), BuyAndHoldStrategy)


def test_unknown_strategy_lists_the_available_ones():
    with pytest.raises(InvalidStrategyError, match="Available: buy_and_hold"):
        create_strategy("magic")


def test_unknown_parameter_raises_invalid_strategy_error():
    with pytest.raises(InvalidStrategyError, match="Invalid parameters"):
        create_strategy("moving_average", window=10)


def test_invalid_parameter_value_raises_invalid_strategy_error():
    with pytest.raises(InvalidStrategyError):
        create_strategy("moving_average", short_window=50, long_window=10)


# -- no look-ahead bias ---------------------------------------------------------


@pytest.mark.parametrize(
    "strategy",
    [
        BuyAndHoldStrategy(),
        MovingAverageStrategy(short_window=5, long_window=20),
        MomentumStrategy(lookback=10),
    ],
)
def test_future_prices_never_change_past_positions(strategy):
    """Adding data at the end must not alter any position already decided."""
    rng = np.random.default_rng(1)
    prices = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 120)))

    full = strategy.positions(prices)
    partial = strategy.positions(prices.iloc[:80])

    assert partial.tolist() == full.iloc[:80].tolist()