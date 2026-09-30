"""Tests for strategies_py.tier_manager."""
from strategies_py.tier_manager import TierManager


def test_tier_manager_loads():
    tm = TierManager()
    assert len(tm.tiers) >= 4
    assert len(tm.strategy_to_tier) > 0


def test_get_tier_known():
    tm = TierManager()
    tier = tm.get_tier("false_breakout")
    assert tier == "tier_1_high_performers"


def test_get_tier_unknown_returns_none():
    tm = TierManager()
    assert tm.get_tier("nonexistent_strategy") is None


def test_get_weight_matches_tier():
    tm = TierManager()
    assert tm.get_weight("false_breakout") == 1.0
    assert tm.get_weight("sd_zones") == 0.7
    assert tm.get_weight("mad_bb") == 0.5
    assert tm.get_weight("fvg") == 0.0


def test_get_enabled_strategies_for_personal():
    tm = TierManager()
    enabled = tm.get_enabled_strategies("personal")
    assert "false_breakout" in enabled
    assert "sd_zones" in enabled
    assert "mad_bb" in enabled
    assert "fvg" not in enabled


def test_stats_includes_tiers_and_accounts():
    tm = TierManager()
    s = tm.stats()
    assert "tiers" in s
    assert "accounts" in s
    assert "personal" in s["accounts"]
    assert "prop" in s["accounts"]
