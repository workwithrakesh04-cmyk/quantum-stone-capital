"""Tests for strategies_py.base."""
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class _Dummy(BaseStrategy):
    NAME = "dummy"
    TIMEFRAMES = ["5m"]

    def analyze(self, candles):
        return self._hold_signal("nothing")


def test_base_strategy_subclass_instantiates():
    s = _Dummy(timeframe="5m")
    assert s.timeframe == "5m"
    assert s.NAME == "dummy"


def test_hold_signal_returns_hold():
    s = _Dummy()
    sig = s.analyze([])
    assert isinstance(sig, Signal)
    assert sig.direction == "HOLD"
    assert sig.confidence == 0.0
    assert sig.strategy == "dummy"


def test_candle_helpers():
    s = _Dummy()
    bull = {"open": 100, "high": 110, "low": 99, "close": 108, "volume": 1}
    bear = {"open": 108, "high": 109, "low": 100, "close": 100, "volume": 1}
    assert s._candle_body(bull) == 8
    assert s._candle_range(bull) == 11
    assert s._is_bullish(bull) is True
    assert s._is_bearish(bear) is True


def test_engulfing_helpers():
    s = _Dummy()
    prev_bear = {"open": 100, "high": 101, "low": 95, "close": 96}
    curr_bull = {"open": 95, "high": 105, "low": 94, "close": 104}
    assert s._is_engulfing_bullish(prev_bear, curr_bull) is True

    prev_bull = {"open": 96, "high": 105, "low": 95, "close": 104}
    curr_bear = {"open": 105, "high": 106, "low": 94, "close": 95}
    assert s._is_engulfing_bearish(prev_bull, curr_bear) is True


def test_avg_helpers():
    s = _Dummy()
    candles = [
        {"open": 100, "high": 110, "low": 90, "close": 100, "volume": 10},
        {"open": 100, "high": 120, "low": 90, "close": 100, "volume": 20},
    ]
    assert s._avg_volume(candles, n=2) == 15
    assert s._avg_range(candles, n=2) == 25


def test_get_rule_weight_default():
    s = _Dummy()
    assert s._get_rule_weight("long") == 0.5
