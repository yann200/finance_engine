"""Shared pytest fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """Four days of prices in the standard format (index 'date', close, volume)."""
    index = pd.DatetimeIndex(
        ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"], name="date"
    )
    return pd.DataFrame(
        {"close": [100.0, 110.0, 99.0, 99.0], "volume": [1000, 1100, 900, 950]},
        index=index,
    )