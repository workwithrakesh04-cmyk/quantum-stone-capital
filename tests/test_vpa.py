"""Tests for VPA engine."""
import pytest
from core.vpa import VPAEngine, VPABar


@pytest.fixture
def engine():
    return VPAEngine(avg_volume_window=5)


def _history(vol=100, spread=1.0, n=10):
    return [VPABar(high=100 + spread, low=100, close=100 + spread / 2,
                   open=100, volume=vol) for _ in range(n)]


def test_classify_high_vol_wide_spread(engine):
    history = _history()
    bar = VPABar(high=105, low=100, close=104, open=101, volume=300)
    assert engine.classify_bar(bar, history) == "high_volume_wide_spread"


def test_classify_high_vol_narrow_spread(engine):
    history = _history()
    bar = VPABar(high=100.3, low=100.0, close=100.2, open=100.1, volume=300)
    assert engine.classify_bar(bar, history) == "high_volume_narrow_spread"


def test_classify_low_vol_wide_spread(engine):
    history = _history()
    bar = VPABar(high=105, low=100, close=104, open=101, volume=50)
    assert engine.classify_bar(bar, history) == "low_volume_wide_spread"


def test_classify_low_vol_narrow_spread(engine):
    history = _history()
    bar = VPABar(high=100.3, low=100.0, close=100.2, open=100.1, volume=50)
    assert engine.classify_bar(bar, history) == "low_volume_narrow_spread"


def test_classify_insufficient_history(engine):
    bar = VPABar(high=105, low=100, close=104, open=101, volume=300)
    assert engine.classify_bar(bar, []) is None


def test_effort_vs_result_confirm(engine):
    history = _history()
    bar = VPABar(high=105, low=100, close=104, open=100, volume=300)
    assert engine.effort_vs_result(bar, history) == "confirm"


def test_effort_vs_result_divergence(engine):
    history = _history()
    bar = VPABar(high=100.2, low=100.0, close=100.1, open=100.0, volume=300)
    assert engine.effort_vs_result(bar, history) == "divergence"


def test_effort_vs_result_weak(engine):
    history = _history()
    bar = VPABar(high=105, low=100, close=104, open=100, volume=50)
    assert engine.effort_vs_result(bar, history) == "weak"


def test_effort_vs_result_quiet(engine):
    history = _history()
    bar = VPABar(high=100.5, low=100.3, close=100.4, open=100.35, volume=100)
    assert engine.effort_vs_result(bar, history) == "quiet"


def test_effort_vs_result_insufficient(engine):
    bar = VPABar(high=105, low=100, close=104, open=100, volume=300)
    assert engine.effort_vs_result(bar, []) == "quiet"
