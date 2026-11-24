"""Unit tests for MovingAverageStrategy (expected values computed by hand)."""

import logging

import numpy as np
import pytest

from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.moving_average import MovingAverageStrategy

# short = 2 days, long = 3 days
PRICES = [10.0, 11.0, 12.0, 11.0, 10.0, 9.0, 10.0, 12.0]
# SMA2: nan, 10.5, 11.5, 11.5, 10.5,  9.5,  9.5, 11.0
# SMA3: nan, nan,  11.0, 11.33, 11.0, 10.0, 9.67, 10.33
# SMA2 > SMA3 ?  no,  no, yes, yes, no, no, no, yes


@pytest.fixture
def strategy():
    return MovingAverageStrategy(short_window=2, long_window=3)


def test_signals(strategy):
    assert strategy.generate_signals(PRICES).tolist() == [0, 0, 1, 1, 0, 0, 0, 1]


def test_positions_are_delayed_by_one_day(strategy):
    assert strategy.positions(PRICES).tolist() == [0, 0, 0, 1, 1, 0, 0, 0]


def test_gross_returns(strategy):
    # invested on days 3 and 4 only: 11/12 - 1 and 10/11 - 1
    expected = [0.0, 0.0, -1 / 12, -1 / 11, 0.0, 0.0, 0.0]
    assert strategy.gross_returns(PRICES).tolist() == pytest.approx(expected)


def test_rising_prices_give_a_buy_signal_after_the_warm_up(strategy):
    signals = strategy.generate_signals(np.arange(1.0, 11.0))
    assert signals.tolist() == [0, 0] + [1] * 8


def test_falling_prices_never_give_a_buy_signal(strategy):
    assert strategy.generate_signals(np.arange(10.0, 0.0, -1.0)).sum() == 0


def test_warns_when_there_are_fewer_prices_than_the_long_window(caplog):
    strategy = MovingAverageStrategy(short_window=2, long_window=50)

    with caplog.at_level(logging.WARNING):
        signals = strategy.generate_signals([10.0, 11.0, 12.0])

    assert signals.sum() == 0
    assert "no signal can be generated" in caplog.text


@pytest.mark.parametrize(
    "short, long",
    [(5, 5), (10, 5), (0, 5), (-1, 5), (2.5, 5), (2, "5")],
)
def test_invalid_windows_raise(short, long):
    with pytest.raises(InvalidStrategyError):
        MovingAverageStrategy(short_window=short, long_window=long)


def test_params_and_repr():
    strategy = MovingAverageStrategy(20, 100)
    assert strategy.params() == {"short_window": 20, "long_window": 100}
    assert repr(strategy) == "MovingAverageStrategy(short_window=20, long_window=100)"


def test_defaults_are_50_and_200():
    strategy = MovingAverageStrategy()
    assert (strategy.short_window, strategy.long_window) == (50, 200)