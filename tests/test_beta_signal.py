"""Tests for beta_brain.signal."""
from beta_brain.signal import Signal


def test_default_fields():
    s = Signal(strategy="foo", direction="LONG", confidence=0.7)
    assert s.timeframe == "5m"
    assert s.weight == 0.5
    assert s.confluences == []


def test_is_actionable_long():
    s = Signal(strategy="foo", direction="LONG", confidence=0.6)
    assert s.is_actionable() is True


def test_is_actionable_low_confidence():
    s = Signal(strategy="foo", direction="LONG", confidence=0.3)
    assert s.is_actionable() is False


def test_is_actionable_hold():
    s = Signal(strategy="foo", direction="HOLD", confidence=0.9)
    assert s.is_actionable() is False


def test_direction_helpers():
    assert Signal("a", "LONG", 0.5).is_long() is True
    assert Signal("a", "SHORT", 0.5).is_short() is True
    assert Signal("a", "HOLD", 0.5).is_hold() is True


def test_to_dict():
    s = Signal(strategy="foo", direction="LONG", confidence=0.5)
    d = s.to_dict()
    assert d["strategy"] == "foo"
    assert d["direction"] == "LONG"
