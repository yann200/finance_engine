"""Lookup of strategies by name, used by the CLI and configuration files."""

from __future__ import annotations

from finance_engine.exceptions import InvalidStrategyError
from finance_engine.strategies.base import Strategy
from finance_engine.strategies.buy_and_hold import BuyAndHoldStrategy
from finance_engine.strategies.momentum import MomentumStrategy
from finance_engine.strategies.moving_average import MovingAverageStrategy

STRATEGIES: dict[str, type[Strategy]] = {
    "buy_and_hold": BuyAndHoldStrategy,
    "moving_average": MovingAverageStrategy,
    "momentum": MomentumStrategy,
}


def available_strategies() -> list[str]:
    """Return the names of the registered strategies, sorted."""
    return sorted(STRATEGIES)


def create_strategy(name: str, **params) -> Strategy:
    """Build a strategy from its registered name and keyword parameters.

    Example:
        >>> create_strategy("moving_average", short_window=20, long_window=100)

    Raises:
        InvalidStrategyError: If the name is unknown, a parameter does not
            exist, or a parameter value is invalid.
    """
    key = name.strip().lower()
    try:
        strategy_class = STRATEGIES[key]
    except KeyError:
        raise InvalidStrategyError(
            f"Unknown strategy '{name}'. Available: {', '.join(available_strategies())}"
        ) from None
    try:
        return strategy_class(**params)
    except TypeError as exc:  # unexpected keyword argument
        raise InvalidStrategyError(f"Invalid parameters for '{key}': {exc}") from exc