"""Tests for footprint engine."""
import pytest
from core.footprint import FootprintEngine, FootprintBar, FootprintLevel


@pytest.fixture
def engine():
    return FootprintEngine()


def _simple_ticks():
    return [
        {"price": 100.0, "volume": 50, "side": "bid"},
        {"price": 100.0, "volume": 30, "side": "ask"},
        {"price": 101.0, "volume": 200, "side": "ask"},
        {"price": 101.0, "volume": 20, "side": "bid"},
        {"price": 102.0, "volume": 100, "side": "bid"},
    ]


def test_build_bar_levels(engine):
    bar = engine.build_bar(_simple_ticks())
    assert len(bar.levels) == 3


def test_build_bar_poc(engine):
    bar = engine.build_bar(_simple_ticks())
    # 101 has total 220 -> highest volume -> POC
    assert bar.poc == 101.0


def test_total_volume(engine):
    bar = engine.build_bar(_simple_ticks())
    assert bar.total_volume == 400.0


def test_delta(engine):
    bar = engine.build_bar(_simple_ticks())
    # deltas: 100: 30-50=-20; 101: 200-20=180; 102: 0-100=-100
    # total = -20+180-100 = 60
    assert bar.delta == 60.0


def test_level_delta(engine):
    lvl = FootprintLevel(price=100.0, bid_volume=10.0, ask_volume=40.0)
    assert lvl.delta == 30.0


def test_level_total_volume(engine):
    lvl = FootprintLevel(price=100.0, bid_volume=10.0, ask_volume=40.0)
    assert lvl.total_volume == 50.0


def test_find_imbalances(engine):
    bar = engine.build_bar(_simple_ticks())
    imbalances = engine.find_imbalances(bar, ratio=3.0)
    # 101: 200/20 = 10 -> imbalance
    prices = [l.price for l in imbalances]
    assert 101.0 in prices


def test_no_imbalances_when_balanced(engine):
    ticks = [
        {"price": 100.0, "volume": 50, "side": "bid"},
        {"price": 100.0, "volume": 55, "side": "ask"},
    ]
    bar = engine.build_bar(ticks)
    assert engine.find_imbalances(bar, ratio=3.0) == []


def test_absorption_insufficient_volume(engine):
    bar = engine.build_bar(_simple_ticks())
    assert engine.detect_absorption(bar, min_total_volume=10000) is None


def test_empty_footprint(engine):
    bar = engine.build_bar([])
    assert bar.poc is None
    assert bar.total_volume == 0.0
    assert bar.delta == 0.0
