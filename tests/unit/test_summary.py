"""Unit tests for the performance summary."""

import pytest

from finance_engine.analytics import summarize
from finance_engine.analytics.summary import PerformanceSummary
from finance_engine.exceptions import InsufficientDataError

PRICES = [100.0, 110.0, 99.0, 99.0]


def test_summary_values():
    summary = summarize(PRICES)

    assert summary.n_observations == 3
    assert summary.total_return == pytest.approx(-0.01)   # 99 / 100 - 1
    assert summary.max_drawdown == pytest.approx(-0.10)   # 110 -> 99
    assert summary.volatility > 0


def test_summary_is_immutable():
    summary = summarize(PRICES)
    with pytest.raises(Exception):  # FrozenInstanceError
        summary.total_return = 1.0


def test_summary_as_dict_has_all_fields():
    data = summarize(PRICES).as_dict()
    assert set(data) == {
        "total_return", "annualized_return", "volatility",
        "sharpe_ratio", "max_drawdown", "var_95", "n_observations",
    }


def test_summary_text_is_readable():
    text = str(summarize(PRICES))
    assert "Sharpe ratio" in text
    assert "Max drawdown" in text
    assert "-10.00%" in text


def test_summary_is_a_performance_summary():
    assert isinstance(summarize(PRICES), PerformanceSummary)


def test_summary_needs_enough_prices():
    with pytest.raises(InsufficientDataError):
        summarize([100.0, 101.0])  # a single return is not enough for volatility