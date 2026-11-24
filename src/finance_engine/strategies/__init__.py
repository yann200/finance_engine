"""Trading strategies and their registry."""

from finance_engine.strategies.base import Strategy
from finance_engine.strategies.buy_and_hold import BuyAndHoldStrategy
from finance_engine.strategies.momentum import MomentumStrategy
from finance_engine.strategies.moving_average import MovingAverageStrategy
from finance_engine.strategies.registry import available_strategies, create_strategy

__all__ = [
    "BuyAndHoldStrategy",
    "MomentumStrategy",
    "MovingAverageStrategy",
    "Strategy",
    "available_strategies",
    "create_strategy",
]