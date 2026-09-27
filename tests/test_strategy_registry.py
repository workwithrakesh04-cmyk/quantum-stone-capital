"""Tests for StrategyRegistry."""
import pytest
from strategies.registry import StrategyRegistry


@pytest.fixture
def registry():
    return StrategyRegistry(root="strategies")


def test_registry_loads(registry):
    assert registry.count() > 0


def test_registry_contains_known_strategies(registry):
    names = registry.all_names()
    for expected in ("bb_9ema", "double_rsi", "smc_ob_retest", "turtle_system1"):
        assert expected in names, "missing: " + expected


def test_get_returns_dict(registry):
    spec = registry.get("bb_9ema")
    assert spec is not None
    assert spec.get("type") == "swing"


def test_get_unknown_returns_none(registry):
    assert registry.get("nonexistent_strategy_xyz") is None


def test_by_category(registry):
    swing = registry.by_category("swing")
    assert "bb_9ema" in swing


def test_match_regime_trending(registry):
    matches = registry.match_regime("trending")
    assert "vcp" in matches
    assert "turtle_system1" in matches


def test_match_regime_ranging(registry):
    matches = registry.match_regime("ranging")
    assert "gartley_bull" in matches


def test_match_regime_with_timeframe_filter(registry):
    matches = registry.match_regime("trending", timeframe="1d")
    assert "vcp" in matches
    # bb_9ema is 30m only, should not appear when filtering 1d
    assert "bb_9ema" not in matches
