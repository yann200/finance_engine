"""Unit tests for return calculations (expected values computed by hand)."""

import numpy as np
import pandas as pd
import pytest

from finance_engine.analytics.returns import (
    annualized_return,
    cumulative_return,
    daily_returns,
    equity_curve,
)
from finance_engine.exceptions import InsufficientDataError


# -- daily_returns -------------------------------------------------------------


def test_daily_returns_values():
    # 100 -> 110 is +10 %, 110 -> 99 is -10 %
    assert daily_returns([100.0, 110.0, 99.0]).tolist() == pytest.approx([0.1, -0.1])


def test_daily_returns_has_one_fewer_value_than_prices():
    assert len(daily_returns([100.0, 101.0, 102.0, 103.0])) == 3


def test_daily_returns_keeps_the_dates(sample_prices):
    returns = daily_returns(sample_prices["close"])
    assert returns.index[0] == pd.Timestamp("2024-01-02")


def test_daily_returns_ignores_missing_prices():
    assert len(daily_returns([100.0, np.nan, 110.0, 121.0])) == 2


@pytest.mark.parametrize("prices", [[], [100.0]])
def test_daily_returns_needs_two_prices(prices):
    with pytest.raises(InsufficientDataError):
        daily_returns(prices)


def test_daily_returns_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        daily_returns([100.0, 0.0, 50.0])


# -- cumulative_return ---------------------------------------------------------


def test_cumulative_return_compounds():
    # +10 % then -10 % is -1 % overall (1.1 * 0.9 - 1), not 0 %
    assert cumulative_return([0.1, -0.1]) == pytest.approx(-0.01)


def test_cumulative_return_matches_first_to_last_price():
    prices = [100.0, 110.0, 99.0, 120.0]
    assert cumulative_return(daily_returns(prices)) == pytest.approx(120 / 100 - 1)


def test_cumulative_return_of_empty_series_raises():
    with pytest.raises(InsufficientDataError):
        cumulative_return([])


# -- equity_curve --------------------------------------------------------------


def test_equity_curve_starts_from_initial_value():
    curve = equity_curve([0.1, -0.1], initial_value=100.0)
    assert curve.tolist() == pytest.approx([110.0, 99.0])


def test_equity_curve_default_initial_value_is_one():
    assert equity_curve([0.5]).tolist() == pytest.approx([1.5])


# -- annualized_return ---------------------------------------------------------


def test_annualized_return_when_period_is_one_year():
    # two yearly returns of +10 % -> total +21 %, over 2 years -> +10 % a year
    assert annualized_return([0.1, 0.1], periods_per_year=1) == pytest.approx(0.1)


def test_annualized_return_over_exactly_one_year():
    # two half-yearly returns of +10 % -> +21 % in exactly one year
    assert annualized_return([0.1, 0.1], periods_per_year=2) == pytest.approx(0.21)


def test_annualized_return_rejects_invalid_periods():
    with pytest.raises(ValueError):
        annualized_return([0.1], periods_per_year=0)