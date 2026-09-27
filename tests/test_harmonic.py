"""Tests for Harmonic Pattern engine."""
import pytest
from core.harmonic import HarmonicEngine


@pytest.fixture
def engine():
    return HarmonicEngine()


# --- Gartley ---
def test_gartley_bullish_detects(engine):
    # X=100, A=200, B=140, C=175 (AB/XA=0.6, BC/AB=0.58)
    p = engine.detect_gartley(100.0, 200.0, 140.0, 175.0)
    assert p is not None
    assert p.name == "gartley"


def test_gartley_bearish_detects(engine):
    p = engine.detect_gartley(200.0, 100.0, 160.0, 125.0)
    assert p is not None
    assert p.name == "gartley"


def test_gartley_rejects_wrong_ratios(engine):
    # AB/XA = 1.5 (way out of range)
    p = engine.detect_gartley(100.0, 200.0, 250.0, 240.0)
    assert p is None


# --- Butterfly ---
def test_butterfly_detects(engine):
    # AB/XA = 0.78 (in range 0.75-0.82)
    p = engine.detect_butterfly(100.0, 200.0, 122.0, 140.0)
    assert p is not None
    assert p.name == "butterfly"


def test_butterfly_rejects(engine):
    p = engine.detect_butterfly(100.0, 200.0, 160.0, 140.0)  # AB/XA = 0.6
    assert p is None


# --- Cypher ---
def test_cypher_detects(engine):
    # AB/XA = 0.5, BC/AB = 1.2
    # X=100, A=200, AB=50 => B=150; BC=60 => C=90
    p = engine.detect_cypher(100.0, 200.0, 150.0, 90.0)
    assert p is not None
    assert p.name == "cypher"


# --- Shark ---
def test_shark_always_detects(engine):
    p = engine.detect_shark(100.0, 150.0, 130.0, 145.0)
    assert p is not None
    assert p.name == "shark"


# --- AB=CD ---
def test_abcd_detects(engine):
    # A=100, B=150 (AB=50), C=130 (BC=20, ratio=0.4 -- not in range)
    p = engine.detect_abcd(100.0, 150.0, 130.0)
    assert p is None  # because BC/AB = 0.4 not in [0.55, 0.72]


def test_abcd_valid(engine):
    # A=100, B=150 (AB=50), C=120 (BC=30, ratio=0.6 -- in range)
    p = engine.detect_abcd(100.0, 150.0, 120.0)
    assert p is not None
    assert p.name == "ab_cd"


# --- PCI ---
def test_pci_contains_ideal(engine):
    p = engine.detect_gartley(100.0, 200.0, 140.0, 175.0)
    assert engine.in_pci(p.D_ideal, p) is True


def test_pci_rejects_far_price(engine):
    p = engine.detect_gartley(100.0, 200.0, 140.0, 175.0)
    assert engine.in_pci(p.D_ideal * 2, p) is False


def test_stop_loss_below_pci(engine):
    p = engine.detect_gartley(100.0, 200.0, 140.0, 175.0)
    sl = engine.stop_loss(p)
    assert sl < p.pci_low


def test_pci_width_is_symmetric(engine):
    p = engine.detect_gartley(100.0, 200.0, 140.0, 175.0)
    upper = p.pci_high - p.D_ideal
    lower = p.D_ideal - p.pci_low
    assert abs(upper - lower) < 1e-9
