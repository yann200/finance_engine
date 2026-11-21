"""Unit tests for risk metrics (expected values computed by hand)."""

import math

import numpy as np
import pandas as pd
import pytest

from finance_engine.analytics.risk import (
    correlation_matrix,
    drawdown_series,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
    volatility,
)
from finance_engine.exceptions import InsufficientDataError

# Sample std of [0.01, -0.01, 0.01, -0.01]: sqrt(4 * 0.0001 / 3) = 0.0115470...
ALTERNATING = [0.01, -0.01, 0.01, -0.01]
ALTERNATING_STD = 0.01 * math.sqrt(4 / 3)


# -- volatility ----------------------------------------------------------------


def test_volatility_without_annualisation():
    assert volatility(ALTERNATING, periods_per_year=1) == pytest.approx(ALTERNATING_STD)


def test_volatility_is_annualised_with_square_root_of_time():
    assert volatility(ALTERNATING, periods_per_year=252) == pytest.approx(
        ALTERNATING_STD * math.sqrt(252)
    )


def test_volatility_of_constant_returns_is_zero():
    assert volatility([0.01, 0.01, 0.01]) == pytest.approx(0.0, abs=1e-12)


def test_volatility_needs_two_returns():
    with pytest.raises(InsufficientDataError):
        volatility([0.01])


def test_volatility_rejects_invalid_periods():
    with pytest.raises(ValueError):
        volatility(ALTERNATING, periods_per_year=-1)


# -- sharpe_ratio ---------------------------------------------------------------


def test_sharpe_ratio_value():
    # mean = 0.01, std = 0.011547 -> 0.866 (not annualised)
    assert sharpe_ratio([0.02, 0.0, 0.02, 0.0], periods_per_year=1) == pytest.approx(
        0.01 / ALTERNATING_STD
    )


def test_sharpe_ratio_is_annualised():
    returns = [0.02, 0.0, 0.02, 0.0]
    assert sharpe_ratio(returns, periods_per_year=252) == pytest.approx(
        sharpe_ratio(returns, periods_per_year=1) * math.sqrt(252)
    )


def test_sharpe_ratio_is_zero_when_return_equals_risk_free_rate():
    # per-period risk-free rate = 0.04 / 4 = 0.01 = the mean return
    value = sharpe_ratio([0.02, 0.0, 0.02, 0.0], risk_free_rate=0.04, periods_per_year=4)
    assert abs(value) < 1e-9


def test_sharpe_ratio_decreases_with_higher_risk_free_rate():
    returns = [0.02, 0.0, 0.02, 0.0]
    assert sharpe_ratio(returns, risk_free_rate=0.05) < sharpe_ratio(returns)


def test_sharpe_ratio_is_nan_when_returns_never_vary():
    assert math.isnan(sharpe_ratio([0.01] * 5))


def test_sharpe_ratio_needs_two_returns():
    with pytest.raises(InsufficientDataError):
        sharpe_ratio([0.01])


# -- drawdown ------------------------------------------------------------------

PRICES = [100.0, 120.0, 90.0, 110.0, 80.0]


def test_drawdown_series_values():
    # running maximum: 100, 120, 120, 120, 120
    assert drawdown_series(PRICES).tolist() == pytest.approx(
        [0.0, 0.0, -0.25, -1 / 12, -1 / 3]
    )


def test_drawdown_series_keeps_the_index(sample_prices):
    assert drawdown_series(sample_prices["close"]).index.equals(sample_prices.index)


def test_max_drawdown_is_the_worst_drop_from_a_peak():
    # worst: 120 -> 80, i.e. -33.3 %
    assert max_drawdown(PRICES) == pytest.approx(-1 / 3)


def test_max_drawdown_is_zero_for_a_rising_series():
    assert max_drawdown([100.0, 101.0, 105.0]) == 0.0


def test_max_drawdown_accepts_a_plain_list():
    assert max_drawdown([100.0, 120.0, 90.0]) == pytest.approx(-0.25)


def test_max_drawdown_needs_two_prices():
    with pytest.raises(InsufficientDataError):
        max_drawdown([100.0])


def test_max_drawdown_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        max_drawdown([100.0, -5.0])


# -- value_at_risk -------------------------------------------------------------


@pytest.fixture
def evenly_spread_returns():
    """101 returns from -10 % to +10 %, in steps of 0.2 %."""
    return pd.Series(np.linspace(-0.10, 0.10, 101))


def test_var_95(evenly_spread_returns):
    # 5th percentile sits at index 5 -> -0.10 + 5 * 0.002 = -0.09
    assert value_at_risk(evenly_spread_returns, 0.95) == pytest.approx(-0.09)


def test_var_99_is_worse_than_var_95(evenly_spread_returns):
    assert value_at_risk(evenly_spread_returns, 0.99) == pytest.approx(-0.098)
    assert value_at_risk(evenly_spread_returns, 0.99) < value_at_risk(
        evenly_spread_returns, 0.95
    )


@pytest.mark.parametrize("confidence", [0, 1, -0.5, 1.5])
def test_var_rejects_invalid_confidence(confidence):
    with pytest.raises(ValueError):
        value_at_risk([0.01, -0.02], confidence)


def test_var_of_empty_series_raises():
    with pytest.raises(InsufficientDataError):
        value_at_risk([])


# -- correlation_matrix --------------------------------------------------------


@pytest.fixture
def three_assets():
    a = [0.01, 0.02, -0.01, 0.03]
    return pd.DataFrame({"A": a, "B": [2 * x for x in a], "C": [-x for x in a]})


def test_correlation_of_identical_and_opposite_moves(three_assets):
    corr = correlation_matrix(three_assets)

    assert corr.loc["A", "B"] == pytest.approx(1.0)   # same direction
    assert corr.loc["A", "C"] == pytest.approx(-1.0)  # opposite direction
    assert corr.loc["A", "A"] == pytest.approx(1.0)   # an asset with itself


def test_correlation_needs_a_dataframe():
    with pytest.raises(TypeError):
        correlation_matrix([0.01, 0.02])


def test_correlation_needs_two_assets():
    with pytest.raises(InsufficientDataError):
        correlation_matrix(pd.DataFrame({"A": [0.01, 0.02, 0.03]}))


def test_correlation_needs_two_common_dates():
    frame = pd.DataFrame({"A": [0.01, np.nan], "B": [np.nan, 0.02]})
    with pytest.raises(InsufficientDataError):
        correlation_matrix(frame)