"""Tests for SignalFilter."""
import pytest
from strategies.signal_filter import SignalFilter


@pytest.fixture
def sf():
    return SignalFilter(min_z_score=1.5, scale_max=3.0)


def test_z_score_zero_std(sf):
    assert sf.z_score(5.0, 5.0, 0.0) == 0.0


def test_z_score_standard(sf):
    assert sf.z_score(7.0, 5.0, 1.0) == 2.0


def test_score_rejects_middle_signal(sf):
    history = [100, 101, 99, 100, 102, 98, 101, 99, 100, 101]
    # Value 100.5 is well within 1 std - middle signal
    score = sf.score(100.5, history)
    assert score == 0.0


def test_score_keeps_extreme_signal(sf):
    history = [100, 101, 99, 100, 102, 98, 101, 99, 100, 101]
    # Value 110 is > 3 std above mean -> extreme
    score = sf.score(110.0, history)
    assert score > 0.0
    assert score <= 1.0


def test_passes_true_for_extreme(sf):
    history = [100, 101, 99, 100, 102, 98, 101, 99, 100, 101]
    assert sf.passes(110.0, history) is True


def test_passes_false_for_middle(sf):
    history = [100, 101, 99, 100, 102, 98, 101, 99, 100, 101]
    assert sf.passes(100.5, history) is False


def test_score_insufficient_history(sf):
    assert sf.score(110.0, [100.0]) == 0.0
