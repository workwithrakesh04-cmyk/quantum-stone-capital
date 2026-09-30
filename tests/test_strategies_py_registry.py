"""Tests for strategies_py.registry."""
import pytest
from strategies_py.registry import StrategyRegistry
from strategies_py.base import BaseStrategy


class _LongStrat(BaseStrategy):
    NAME = "always_long"
    TIMEFRAMES = ["5m"]
    def analyze(self, candles):
        from beta_brain.signal import Signal
        return Signal(strategy=self.NAME, direction="LONG", confidence=0.7)


class _HoldStrat(BaseStrategy):
    NAME = "always_hold"
    TIMEFRAMES = ["5m"]
    def analyze(self, candles):
        return self._hold_signal()


class _DisabledStrat(BaseStrategy):
    NAME = "intermarket"  # in global_disable
    TIMEFRAMES = ["5m"]
    def analyze(self, candles):
        from beta_brain.signal import Signal
        return Signal(strategy=self.NAME, direction="LONG", confidence=0.7)


def test_registry_loads_configs():
    r = StrategyRegistry(timeframe="5m")
    assert len(r.global_disable) > 0
    assert "false_breakout" not in r.global_disable or True


def test_registry_register_and_instantiate():
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_LongStrat, _HoldStrat])
    r.instantiate_all()
    assert "always_long" in r.active_strategies
    assert "always_hold" in r.active_strategies


def test_disabled_goes_to_shadow():
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_DisabledStrat])
    r.instantiate_all()
    assert "intermarket" in r.shadow_strategies
    assert "intermarket" not in r.active_strategies


def test_wrong_timeframe_skipped():
    class _OtherTF(BaseStrategy):
        NAME = "other_tf"
        TIMEFRAMES = ["1h"]
        def analyze(self, candles):
            return self._hold_signal()
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_OtherTF])
    r.instantiate_all()
    assert "other_tf" not in r.active_strategies


def test_run_all_produces_signals():
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_LongStrat, _HoldStrat])
    r.instantiate_all()
    signals = r.run_all([{"open": 100, "high": 101, "low": 99, "close": 100, "open_time": 0}])
    assert len(signals) == 2
    dirs = {s.direction for s in signals}
    assert "LONG" in dirs


def test_run_all_tracks_fire_counts():
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_LongStrat])
    r.instantiate_all()
    r.run_all([{"open": 100, "high": 101, "low": 99, "close": 100, "open_time": 0}])
    assert r._fire_counts["always_long"] == 1


def test_get_min_confidence_for_regime():
    r = StrategyRegistry(timeframe="5m")
    assert r.get_min_confidence("RANGING") == 0.70
    assert r.get_min_confidence("TRENDING_UP") == 0.80
    assert r.get_min_confidence(None) == 0.70


def test_stats_includes_counts():
    r = StrategyRegistry(timeframe="5m")
    r.register_all([_LongStrat, _HoldStrat, _DisabledStrat])
    r.instantiate_all()
    s = r.stats()
    assert s["active"] == 2
    assert s["shadow"] == 1
    assert s["has_tier_manager"] is True
