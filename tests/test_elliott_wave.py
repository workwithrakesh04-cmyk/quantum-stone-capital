"""Tests for Elliott Wave engine."""
import pytest
from core.elliott_wave import ElliottWaveEngine, WavePoint


@pytest.fixture
def engine():
    return ElliottWaveEngine()


def _valid_impulse():
    return {
        0: WavePoint(price=100.0, index=0),
        1: WavePoint(price=120.0, index=5),
        2: WavePoint(price=110.0, index=10),
        3: WavePoint(price=160.0, index=20),
        4: WavePoint(price=140.0, index=25),
        5: WavePoint(price=180.0, index=35),
    }


def test_valid_impulse(engine):
    result = engine.validate_impulse(_valid_impulse())
    assert result["valid"] is True
    assert result["violations"] == []


def test_rule1_wave2_retraces_too_much(engine):
    waves = _valid_impulse()
    waves[2] = WavePoint(price=95.0, index=10)  # below wave 0
    result = engine.validate_impulse(waves)
    assert result["valid"] is False
    assert any("Rule 1" in v for v in result["violations"])


def test_rule4_wave3_not_exceeding_wave1(engine):
    waves = _valid_impulse()
    waves[3] = WavePoint(price=115.0, index=20)  # below wave 1 (120)
    result = engine.validate_impulse(waves)
    assert result["valid"] is False
    assert any("Rule 4" in v for v in result["violations"])


def test_rule3_wave4_overlaps_wave1(engine):
    waves = _valid_impulse()
    waves[4] = WavePoint(price=115.0, index=25)  # overlaps wave 1 (120)
    result = engine.validate_impulse(waves)
    assert result["valid"] is False
    assert any("Rule 3" in v for v in result["violations"])


def test_rule6_wave4_retraces_over_100pct(engine):
    waves = _valid_impulse()
    waves[4] = WavePoint(price=105.0, index=25)  # below wave 2 (110)
    result = engine.validate_impulse(waves)
    assert result["valid"] is False
    assert any("Rule 6" in v for v in result["violations"])


def test_missing_waves(engine):
    result = engine.validate_impulse({0: WavePoint(100.0, 0)})
    assert result["valid"] is False


def test_wave3_targets_basic(engine):
    targets = engine.wave3_targets(w1_start=100.0, w1_end=120.0, w2_end=110.0)
    # w1_len = 20; w2_end + 1.618*20 = 110 + 32.36 = 142.36
    assert abs(targets["1.618"] - 142.36) < 0.01
    assert "0.618" in targets
    assert "2.618" in targets


def test_wave5_targets_basic(engine):
    targets = engine.wave5_targets(w4_end=140.0, w3_len=50.0)
    assert abs(targets["0.618"] - (140.0 + 0.618 * 50.0)) < 0.01
    assert "1.618" in targets


def test_invalidation_level_with_wave4(engine):
    waves = _valid_impulse()
    # Should return wave 2 price (110) as invalidation for wave 5
    assert engine.invalidation_level(waves) == 110.0


def test_invalidation_level_empty(engine):
    assert engine.invalidation_level({}) == 0.0
