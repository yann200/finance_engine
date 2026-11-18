"""Reusable decorators.

Current content:
    timer: log how long a function takes to run.
    retry: re-run a function when it fails with a transient error.
"""

import functools
import logging
import time
from typing import Callable, ParamSpec, TypeVar

from finance_engine.exceptions import DataProviderError, InvalidTickerError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def timer(func: Callable[P, R]) -> Callable[P, R]:
    """Log the execution time of the decorated function at INFO level.

    The time is logged even if the function raises an exception, and the
    exception is propagated unchanged.

    Example:
        >>> @timer
        ... def compute() -> int:
        ...     return 42
    """

    @functools.wraps(func)  # keep the original name and docstring
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.info("%s executed in %.4f s", func.__qualname__, elapsed)

    return wrapper


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (DataProviderError,),
    give_up_on: tuple[type[BaseException], ...] = (InvalidTickerError,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry the decorated function when it raises a transient error.

    This is a decorator *factory*: it is called with parameters and returns
    the actual decorator.

    Args:
        attempts: Maximum number of calls (first try included). Must be >= 1.
        delay: Seconds to wait before the second attempt.
        backoff: Multiplier applied to the delay after each failure
            (``delay=1, backoff=2`` waits 1 s, then 2 s, then 4 s...).
        retry_on: Exceptions that trigger a new attempt.
        give_up_on: Exceptions re-raised immediately, even if they are also
            instances of ``retry_on`` (checked first). Retrying a ticker that
            does not exist would be pointless.

    Raises:
        ValueError: If ``attempts`` is lower than 1.

    The last exception is re-raised unchanged once all attempts are used.

    Example:
        >>> @retry(attempts=3, delay=0.5)
        ... def download() -> None:
        ...     ...
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except give_up_on:
                    raise  # permanent error: retrying cannot help
                except retry_on as exc:
                    if attempt == attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__, attempts, exc,
                        )
                        raise
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %.1f s",
                        func.__qualname__, attempt, attempts, exc, wait,
                    )
                    time.sleep(wait)
                    wait *= backoff
            raise RuntimeError("unreachable")  # keeps type checkers happy

        return wrapper

    return decorator