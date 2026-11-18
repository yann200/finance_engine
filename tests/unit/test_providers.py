"""Unit tests for data providers and price validation."""

import logging

import numpy as np
import pandas as pd
import pytest

from finance_engine.data.providers import CsvProvider, YahooProvider, validate_prices
from finance_engine.exceptions import DataProviderError, InvalidTickerError


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make retries instantaneous."""
    monkeypatch.setattr("finance_engine.utils.decorators.time.sleep", lambda s: None)


def raw_frame(dates, close, volume=None, **extra):
    """Build a raw price table like the ones returned by external sources."""
    data = {"Close": close, "Volume": volume if volume is not None else [100] * len(close)}
    data.update(extra)
    return pd.DataFrame(data, index=pd.Index(dates))


# -- validate_prices ----------------------------------------------------------


def test_validate_returns_standard_format():
    raw = raw_frame(["2024-01-02", "2024-01-01"], [11.0, 10.0])

    result = validate_prices(raw, "AAPL")

    assert list(result.columns) == ["close", "volume"]
    assert result.index.name == "date"
    assert result.index.is_monotonic_increasing  # sorted
    assert result["close"].tolist() == [10.0, 11.0]


def test_validate_does_not_modify_its_input():
    raw = raw_frame(["2024-01-01"], [10.0])
    validate_prices(raw, "AAPL")
    assert list(raw.columns) == ["Close", "Volume"]


@pytest.mark.parametrize("empty", [None, pd.DataFrame()])
def test_validate_empty_data_raises_invalid_ticker(empty):
    with pytest.raises(InvalidTickerError):
        validate_prices(empty, "ZZZZ")


def test_validate_missing_column_raises():
    raw = pd.DataFrame({"Close": [10.0]}, index=["2024-01-01"])
    with pytest.raises(DataProviderError, match="Missing columns"):
        validate_prices(raw, "AAPL")


def test_validate_drops_missing_close_and_warns(caplog):
    raw = raw_frame(["2024-01-01", "2024-01-02"], [10.0, np.nan])

    with caplog.at_level(logging.WARNING):
        result = validate_prices(raw, "AAPL")

    assert len(result) == 1
    assert "without close price" in caplog.text


def test_validate_all_close_missing_raises_invalid_ticker():
    raw = raw_frame(["2024-01-01"], [np.nan])
    with pytest.raises(InvalidTickerError):
        validate_prices(raw, "AAPL")


@pytest.mark.parametrize("bad_close", [0.0, -5.0])
def test_validate_non_positive_close_raises(bad_close):
    raw = raw_frame(["2024-01-01", "2024-01-02"], [10.0, bad_close])
    with pytest.raises(DataProviderError, match="Non-positive"):
        validate_prices(raw, "AAPL")


def test_validate_drops_duplicate_dates_keeping_last():
    raw = raw_frame(["2024-01-01", "2024-01-01"], [10.0, 12.0])

    result = validate_prices(raw, "AAPL")

    assert len(result) == 1
    assert result["close"].iloc[0] == 12.0


def test_validate_missing_volume_becomes_zero():
    raw = raw_frame(["2024-01-01"], [10.0], volume=[np.nan])
    assert validate_prices(raw, "AAPL")["volume"].iloc[0] == 0


def test_validate_strips_timezone_and_time():
    index = pd.DatetimeIndex(["2024-01-01 16:00"], tz="America/New_York")
    raw = pd.DataFrame({"Close": [10.0], "Volume": [1]}, index=index)

    result = validate_prices(raw, "AAPL")

    assert result.index.tz is None
    assert result.index[0] == pd.Timestamp("2024-01-01")


def test_validate_invalid_dates_raise_provider_error():
    raw = raw_frame(["not a date"], [10.0])
    with pytest.raises(DataProviderError, match="Invalid dates"):
        validate_prices(raw, "AAPL")


# -- CsvProvider --------------------------------------------------------------

CSV_CONTENT = """Date,Open,High,Low,Close,Adj Close,Volume
2024-01-03,10,11,9,10.5,10.5,300
2024-01-01,9,10,8,9.5,9.5,100
2024-01-02,9,11,9,10.0,10.0,200
"""


@pytest.fixture
def csv_dir(tmp_path):
    (tmp_path / "AAPL.csv").write_text(CSV_CONTENT)
    return tmp_path


def test_csv_provider_reads_and_sorts(csv_dir):
    prices = CsvProvider(csv_dir).fetch("AAPL")

    assert prices["close"].tolist() == [9.5, 10.0, 10.5]
    assert prices["volume"].tolist() == [100, 200, 300]


def test_csv_provider_ticker_is_case_insensitive(csv_dir):
    assert len(CsvProvider(csv_dir).fetch("aapl")) == 3


def test_csv_provider_filters_dates_inclusively(csv_dir):
    prices = CsvProvider(csv_dir).fetch("AAPL", start="2024-01-02", end="2024-01-03")
    assert prices["close"].tolist() == [10.0, 10.5]


def test_csv_provider_unknown_ticker_raises(csv_dir):
    with pytest.raises(InvalidTickerError):
        CsvProvider(csv_dir).fetch("MSFT")


def test_csv_provider_empty_file_raises_provider_error(tmp_path):
    (tmp_path / "AAPL.csv").write_text("")
    with pytest.raises(DataProviderError):
        CsvProvider(tmp_path).fetch("AAPL")


# -- YahooProvider (with a fake downloader, no network) ------------------------


def yahoo_like_frame():
    """Frame shaped like recent yfinance output: (field, ticker) column pairs."""
    index = pd.DatetimeIndex(["2024-01-01", "2024-01-02"])
    return pd.DataFrame(
        {("Close", "AAPL"): [10.0, 11.0], ("Volume", "AAPL"): [100, 200]},
        index=index,
    )


def test_yahoo_provider_handles_multiindex_columns():
    provider = YahooProvider(downloader=lambda *a, **k: yahoo_like_frame())

    prices = provider.fetch("aapl")

    assert prices["close"].tolist() == [10.0, 11.0]


def test_yahoo_provider_retries_transient_failures():
    calls = {"count": 0}

    def flaky_download(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("network down")
        return yahoo_like_frame()

    prices = YahooProvider(downloader=flaky_download).fetch("AAPL")

    assert calls["count"] == 3
    assert len(prices) == 2


def test_yahoo_provider_wraps_persistent_failures():
    def always_fails(*args, **kwargs):
        raise ConnectionError("network down")

    with pytest.raises(DataProviderError) as error:
        YahooProvider(downloader=always_fails).fetch("AAPL")

    assert isinstance(error.value.__cause__, ConnectionError)  # `raise ... from`


def test_yahoo_provider_does_not_retry_unknown_ticker():
    calls = {"count": 0}

    def empty_download(*args, **kwargs):
        calls["count"] += 1
        return pd.DataFrame()

    with pytest.raises(InvalidTickerError):
        YahooProvider(downloader=empty_download).fetch("ZZZZ")

    assert calls["count"] == 1