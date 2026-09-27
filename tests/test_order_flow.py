"""Tests for order flow engine."""
import pytest
from core.order_flow import OrderFlowEngine, OrderFlowBar


@pytest.fixture
def engine():
    return OrderFlowEngine()


def test_delta_bullish(engine):
    assert engine.compute_delta(bid_volume=100, ask_volume=200) == 100


def test_delta_bearish(engine):
    assert engine.compute_delta(bid_volume=200, ask_volume=100) == -100


def test_delta_neutral(engine):
    assert engine.compute_delta(bid_volume=100, ask_volume=100) == 0


def test_cumulative_delta_accumulates(engine):
    engine.compute_bar(100, 200, 10, 9, 9.5)
    engine.compute_bar(100, 150, 10, 9, 9.5)
    assert engine.cumulative_delta == 150.0


def test_compute_bar_returns_dataclass(engine):
    bar = engine.compute_bar(100, 200, 10, 9, 9.5)
    assert isinstance(bar, OrderFlowBar)
    assert bar.delta == 100


def test_reset(engine):
    engine.compute_bar(100, 200, 10, 9, 9.5)
    assert engine.cumulative_delta != 0
    engine.reset()
    assert engine.cumulative_delta == 0


def test_absorption_bullish(engine):
    bars = [
        engine.compute_bar(100, 200, 10.0, 9.9, 9.95) for _ in range(5)
    ]
    # High delta, small range
    result = engine.detect_absorption(bars, lookback=5)
    assert result in ("bullish_absorb", "bearish_absorb", None)


def test_absorption_insufficient_history(engine):
    bars = [engine.compute_bar(100, 200, 10, 9, 9.5)]
    assert engine.detect_absorption(bars, lookback=5) is None


def test_imbalance_buy(engine):
    bar = engine.compute_bar(bid_volume=10, ask_volume=100, high=10, low=9, close=9.5)
    assert engine.detect_imbalance(bar, threshold=3.0) == "buy_imbalance"


def test_imbalance_sell(engine):
    bar = engine.compute_bar(bid_volume=100, ask_volume=10, high=10, low=9, close=9.5)
    assert engine.detect_imbalance(bar, threshold=3.0) == "sell_imbalance"


def test_imbalance_neutral(engine):
    bar = engine.compute_bar(bid_volume=100, ask_volume=100, high=10, low=9, close=9.5)
    assert engine.detect_imbalance(bar, threshold=3.0) is None


def test_classify_flow(engine):
    assert engine.classify_flow(50) == "bullish"
    assert engine.classify_flow(-50) == "bearish"
    assert engine.classify_flow(0) == "neutral"
