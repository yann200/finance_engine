"""Unit tests for the Asset model."""

from dataclasses import FrozenInstanceError

import pytest

from finance_engine.exceptions import InvalidTickerError
from finance_engine.models.asset import Asset


def test_asset_defaults():
    asset = Asset("AAPL")
    assert asset.ticker == "AAPL"
    assert asset.name == ""
    assert asset.currency == "USD"


def test_ticker_and_currency_are_normalised():
    asset = Asset("  aapl ", name="Apple", currency=" eur")
    assert asset.ticker == "AAPL"
    assert asset.currency == "EUR"


@pytest.mark.parametrize("bad_ticker", ["", "   ", None, 123])
def test_invalid_ticker_raises(bad_ticker):
    with pytest.raises(InvalidTickerError):
        Asset(bad_ticker)


def test_asset_is_immutable():
    asset = Asset("AAPL")
    with pytest.raises(FrozenInstanceError):
        asset.ticker = "MSFT"


def test_equal_assets_are_equal_and_hashable():
    assert Asset("aapl") == Asset("AAPL")
    assert len({Asset("aapl"), Asset("AAPL")}) == 1


def test_str_returns_ticker():
    assert str(Asset("msft")) == "MSFT"