"""Unit tests for the decorators module."""

import logging

import pytest

from finance_engine.exceptions import DataProviderError, InvalidTickerError
from finance_engine.utils.decorators import retry, timer

LOGGER_NAME = "finance_engine.utils.decorators"


# -- timer -------------------------------------------------------------------


def test_timer_returns_the_function_result():
    @timer
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_timer_preserves_function_metadata():
    @timer
    def documented():
        """My docstring."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "My docstring."


def test_timer_logs_execution_time(caplog):
    @timer
    def noop():
        return None

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        noop()

    assert "noop executed in" in caplog.text


def test_timer_logs_and_propagates_exceptions(caplog):
    @timer
    def failing():
        raise ValueError("boom")

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        with pytest.raises(ValueError, match="boom"):
            failing()

    assert "failing executed in" in caplog.text


# -- retry -------------------------------------------------------------------


@pytest.fixture
def sleeps(monkeypatch):
    """Replace time.sleep so tests are instant, and record the waits."""
    recorded = []
    monkeypatch.setattr(
        "finance_engine.utils.decorators.time.sleep", recorded.append
    )
    return recorded


def make_flaky(failures: int, error=DataProviderError):
    """Return a function failing `failures` times, then succeeding."""
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] <= failures:
            raise error("temporary failure")
        return "ok"

    return flaky, calls


def test_retry_succeeds_after_transient_failures(sleeps):
    flaky, calls = make_flaky(failures=2)

    assert retry(attempts=3)(flaky)() == "ok"
    assert calls["count"] == 3


def test_retry_raises_last_error_when_attempts_exhausted(sleeps):
    flaky, calls = make_flaky(failures=10)

    with pytest.raises(DataProviderError):
        retry(attempts=3)(flaky)()
    assert calls["count"] == 3


def test_retry_does_not_retry_give_up_exceptions(sleeps):
    flaky, calls = make_flaky(failures=10, error=InvalidTickerError)

    with pytest.raises(InvalidTickerError):
        retry(attempts=3)(flaky)()
    assert calls["count"] == 1
    assert sleeps == []


def test_retry_does_not_retry_unrelated_exceptions(sleeps):
    flaky, calls = make_flaky(failures=10, error=ValueError)

    with pytest.raises(ValueError):
        retry(attempts=3)(flaky)()
    assert calls["count"] == 1


def test_retry_uses_exponential_backoff(sleeps):
    flaky, _ = make_flaky(failures=10)

    with pytest.raises(DataProviderError):
        retry(attempts=3, delay=1.0, backoff=2.0)(flaky)()
    assert sleeps == [1.0, 2.0]  # no wait after the last attempt


def test_retry_logs_warnings_then_error(sleeps, caplog):
    flaky, _ = make_flaky(failures=10)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        with pytest.raises(DataProviderError):
            retry(attempts=2)(flaky)()

    levels = [record.levelname for record in caplog.records]
    assert levels == ["WARNING", "ERROR"]


def test_retry_rejects_invalid_attempts():
    with pytest.raises(ValueError):
        retry(attempts=0)