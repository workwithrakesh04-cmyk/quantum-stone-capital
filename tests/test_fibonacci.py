"""Tests for Fibonacci helpers."""
import pytest
from utils.fibonacci import (
    retracement_levels,
    extension_levels,
    nearest_ratio,
    RETRACEMENT_RATIOS,
    EXTENSION_RATIOS,
)


def test_retracement_50pct():
    levels = retracement_levels(start=100.0, end=200.0)
    # 50% retracement of 100 -> 200 is 150
    assert abs(levels[0.5] - 150.0) < 1e-9


def test_retracement_618pct():
    levels = retracement_levels(start=100.0, end=200.0)
    # 61.8% retracement: 200 - 0.618 * 100 = 138.2
    assert abs(levels[0.618] - 138.2) < 1e-9


def test_retracement_all_ratios_present():
    levels = retracement_levels(100.0, 200.0)
    for r in RETRACEMENT_RATIOS:
        assert r in levels


def test_extension_1618():
    levels = extension_levels(start=100.0, end=200.0)
    # 1.618 extension: 100 + 1.618 * 100 = 261.8
    assert abs(levels[1.618] - 261.8) < 1e-9


def test_extension_all_ratios_present():
    levels = extension_levels(100.0, 200.0)
    for r in EXTENSION_RATIOS:
        assert r in levels


def test_nearest_ratio_exact():
    assert nearest_ratio(0.618, RETRACEMENT_RATIOS) == 0.618


def test_nearest_ratio_within_tolerance():
    assert nearest_ratio(0.62, RETRACEMENT_RATIOS, tolerance=0.02) == 0.618


def test_nearest_ratio_out_of_tolerance():
    assert nearest_ratio(0.45, RETRACEMENT_RATIOS, tolerance=0.02) == 0.0
