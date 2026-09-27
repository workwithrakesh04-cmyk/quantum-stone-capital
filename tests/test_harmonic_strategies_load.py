"""Test that all harmonic and Elliott Wave strategies load via the registry."""
import pytest
from strategies.registry import StrategyRegistry


@pytest.fixture
def registry():
    return StrategyRegistry(root="strategies")


def test_harmonic_strategies_present(registry):
    names = registry.all_names()
    for expected in ("gartley_bullish", "gartley_bearish",
                     "butterfly_bullish", "butterfly_bearish",
                     "cypher_bullish", "cypher_bearish",
                     "shark_bullish", "shark_bearish",
                     "abcd_bullish", "abcd_bearish"):
        assert expected in names, "missing: " + expected


def test_elliott_wave_strategies_present(registry):
    names = registry.all_names()
    for expected in ("ew_wave3_entry_bullish", "ew_wave3_entry_bearish",
                     "ew_wave5_reversal_bullish", "ew_wave_c_short"):
        assert expected in names, "missing: " + expected


def test_harmonic_count(registry):
    harmonic = registry.by_category("harmonic")
    assert len(harmonic) >= 10


def test_ew_count(registry):
    ew = registry.by_category("elliott_wave")
    assert len(ew) >= 4
