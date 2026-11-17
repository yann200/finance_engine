"""Unit tests for the decorators module."""

import logging

import pytest

from finance_engine.utils.decorators import timer

LOGGER_NAME = "finance_engine.utils.decorators"


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