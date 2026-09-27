"""Test that all ICT/SMC YAML strategies load correctly via the registry."""
import pytest
from strategies.registry import StrategyRegistry


@pytest.fixture
def registry():
    return StrategyRegistry(root="strategies")


def test_fede_ict_strategies_present(registry):
    names = registry.all_names()
    for expected in ("ifvg", "turtle_soup", "mmxm", "breaker_block",
                     "order_block_retest", "liquidity_sweep"):
        assert expected in names, "missing: " + expected


def test_woods_smc_strategies_present(registry):
    names = registry.all_names()
    for expected in ("algo_candle_mitigation", "htf_circle_trade",
                     "ping_pong_1m", "daily_circle_reversal",
                     "strong_high_low_reversal"):
        assert expected in names, "missing: " + expected


def test_crt_strategies_present(registry):
    names = registry.all_names()
    for expected in ("crt_model_1_bearish", "crt_model_1_bullish",
                     "kiss_of_death_bearish", "kiss_of_death_bullish",
                     "candle_3_beginner", "smt_divergence_bearish",
                     "smt_divergence_bullish"):
        assert expected in names, "missing: " + expected


def test_deivid_trap_strategies_present(registry):
    names = registry.all_names()
    for expected in ("trap_double_top", "trap_double_bottom",
                     "trap_fake_breakout_bearish", "trap_fake_breakout_bullish",
                     "trap_head_shoulders", "trap_range_breakout_fade",
                     "ping_pong_range", "premium_discount_reversal"):
        assert expected in names, "missing: " + expected


def test_registry_has_many_ict_strategies(registry):
    ict = registry.by_category("ict_smc")
    assert len(ict) >= 20


def test_ict_strategies_have_min_rr(registry):
    ict = registry.by_category("ict_smc")
    for name in ict:
        spec = registry.get(name)
        assert "min_rr" in spec, name + " missing min_rr"
