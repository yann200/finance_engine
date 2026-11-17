"""Reusable decorators.

Current content:
    timer: log how long a function takes to run.
"""

import functools
import logging
import time
from typing import Callable, ParamSpec, TypeVar

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