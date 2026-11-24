"""Unit tests for MomentumStrategy and BuyAndHoldStrategy."""

import pytest

from finance_engine.analytics import daily_returns
from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.buy_and_hold import BuyAndHoldStrategy
from finance_engine.strategies.momentum import MomentumStrategy

# -- MomentumStrategy ----------------------------------------------------------


def test_signals_follow_the_sign_of_the_past_return():
    prices = [100.0, 98.0, 97.0, 99.0, 96.0, 94.0]
    # return over 2 days: nan, nan, -3 %, +1.02 %, -1.03 %, -5 %
    assert MomentumStrategy(lookback=2).generate_signals(prices).tolist() == [
        0, 0, 0, 1, 0, 0,
    ]


def test_threshold_raises_the_bar():
    prices = [100.0, 100.0, 101.0, 105.0]
    # return over 2 days: nan, nan, +1 %, +5 %
    assert MomentumStrategy(lookback=2).generate_signals(prices).tolist() == [0, 0, 1, 1]
    assert MomentumStrategy(lookback=2, threshold=0.02).generate_signals(prices).tolist() == [
        0, 0, 0, 1,
    ]


def test_cash_during_the_warm_up_period():
    signals = MomentumStrategy(lookback=3).generate_signals([1.0, 2.0, 3.0, 4.0, 5.0])
    assert signals.tolist() == [0, 0, 0, 1, 1]


@pytest.mark.parametrize("lookback", [0, -5, 1.5, "10"])
def test_invalid_lookback_raises(lookback):
    with pytest.raises(InvalidStrategyError):
        MomentumStrategy(lookback=lookback)


@pytest.mark.parametrize("threshold", ["0.1", None, True])
def test_invalid_threshold_raises(threshold):
    with pytest.raises(InvalidStrategyError):
        MomentumStrategy(lookback=5, threshold=threshold)


def test_params_and_repr():
    strategy = MomentumStrategy(lookback=60, threshold=0.01)
    assert strategy.params() == {"lookback": 60, "threshold": 0.01}
    assert repr(strategy) == "MomentumStrategy(lookback=60, threshold=0.01)"


# -- BuyAndHoldStrategy --------------------------------------------------------


def test_buy_and_hold_is_always_invested():
    assert BuyAndHoldStrategy().generate_signals([1.0, 2.0, 3.0]).tolist() == [1, 1, 1]


def test_buy_and_hold_replicates_the_asset_after_the_first_day():
    prices = [100.0, 110.0, 99.0, 120.0]

    gross = BuyAndHoldStrategy().gross_returns(prices)

    assert gross.tolist() == pytest.approx(daily_returns(prices).tolist())