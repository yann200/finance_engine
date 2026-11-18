"""Custom exception hierarchy for finance-engine.

Every exception raised on purpose by the project inherits from
``FinanceEngineError``. Callers can therefore catch either everything coming
from the project, or only a specific kind of failure.

Hierarchy::

    FinanceEngineError
    ├── DataProviderError
    │   └── InvalidTickerError
    ├── RepositoryError
    ├── InsufficientDataError
    └── InvalidStrategyError
"""


class FinanceEngineError(Exception):
    """Base class for all errors raised by finance-engine."""


class DataProviderError(FinanceEngineError):
    """Market data could not be retrieved (network failure, API error)."""


class InvalidTickerError(DataProviderError):
    """A ticker is invalid, unknown, or returned no data."""


class RepositoryError(FinanceEngineError):
    """A database operation failed."""


class InsufficientDataError(FinanceEngineError):
    """There is not enough data to compute the requested metric."""


class InvalidStrategyError(FinanceEngineError):
    """Strategy parameters are inconsistent (e.g. short window >= long window)."""