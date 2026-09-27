"""Tests for Layer 0 data feed."""
import pytest
import pandas as pd
from pathlib import Path

from layers.layer0_data import CSVDataFeed, DataFeedFactory, Bar


@pytest.fixture
def sample_csv(tmp_path):
    """Create a tiny sample OHLCV CSV for testing."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=10, freq="5min", tz="UTC"),
        "open":   [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "high":   [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
        "low":    [ 99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        "close":  [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "volume": [1000] * 10,
    })
    path = tmp_path / "BTCUSD_5m.csv"
    df.to_csv(path, index=False)
    return tmp_path


def test_csv_feed_connect(sample_csv):
    feed = CSVDataFeed(data_dir=str(sample_csv))
    assert feed.connect()


def test_csv_feed_get_bars(sample_csv):
    feed = CSVDataFeed(data_dir=str(sample_csv))
    feed.connect()
    bars = feed.get_bars("BTCUSD", "5m", count=5)
    assert len(bars) == 5
    assert isinstance(bars[0], Bar)
    assert bars[-1].close == 110


def test_csv_feed_missing_file(sample_csv):
    feed = CSVDataFeed(data_dir=str(sample_csv))
    feed.connect()
    with pytest.raises(FileNotFoundError):
        feed.get_bars("EURUSD", "5m", count=5)


def test_latest_price(sample_csv):
    feed = CSVDataFeed(data_dir=str(sample_csv))
    feed.connect()
    feed.get_bars("BTCUSD", "5m", count=5)
    assert feed.get_latest_price("BTCUSD") == 110


def test_factory_csv(sample_csv):
    feed = DataFeedFactory.create("csv", data_dir=str(sample_csv))
    assert isinstance(feed, CSVDataFeed)


def test_factory_unknown():
    with pytest.raises(ValueError):
        DataFeedFactory.create("unknown_feed")
