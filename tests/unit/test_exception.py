"""Unit tests for the exception hierarchy."""

import pytest

from finance_engine.exceptions import (
    DataProviderError,
    FinanceEngineError,
    InsufficientDataError,
    InvalidStrategyError,
    InvalidTickerError,
    RepositoryError,
)


@pytest.mark.parametrize(
    "exc_class",
    [
        DataProviderError,
        InvalidTickerError,
        RepositoryError,
        InsufficientDataError,
        InvalidStrategyError,
    ],
)
def test_all_exceptions_inherit_from_base(exc_class):
    assert issubclass(exc_class, FinanceEngineError)


def test_invalid_ticker_is_a_data_provider_error():
    assert issubclass(InvalidTickerError, DataProviderError)


def test_base_exception_catches_project_errors():
    with pytest.raises(FinanceEngineError):
        raise InsufficientDataError("not enough prices")