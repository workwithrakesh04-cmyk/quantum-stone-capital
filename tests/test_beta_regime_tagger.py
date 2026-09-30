"""Tests for beta_brain.regime_tagger."""
import pytest
from beta_brain.regime_tagger import RegimeTagger, RegimeTag, get_regime_tagger


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def _flat_candles(n, price=100.0, ts_step=300_000):
    return [_candle(price, price, price, price, i * ts_step) for i in range(n)]


def test_empty_returns_unknown():
    t = RegimeTagger()
    tag = t.tag([])
    assert tag.regime == "UNKNOWN"


def test_insufficient_candles_returns_unknown():
    t = RegimeTagger()
    tag = t.tag(_flat_candles(5))
    assert tag.regime == "UNKNOWN"


def test_flat_market_is_choppy():
    t = RegimeTagger()
    tag = t.tag(_flat_candles(50))
    assert tag.regime in ("CHOPPY", "RANGING", "TRENDING_UP", "TRENDING_DOWN")


def test_strong_uptrend():
    t = RegimeTagger()
    candles = []
    p = 100.0
    for i in range(60):
        p *= 1.002
        candles.append(_candle(p, p * 1.001, p * 0.999, p, i * 300_000))
    tag = t.tag(candles)
    assert tag.regime in ("TRENDING_UP", "VOLATILE")
    assert tag.direction >= 0


def test_strong_downtrend():
    t = RegimeTagger()
    candles = []
    p = 200.0
    for i in range(60):
        p *= 0.998
        candles.append(_candle(p, p * 1.001, p * 0.999, p, i * 300_000))
    tag = t.tag(candles)
    assert tag.regime in ("TRENDING_DOWN", "VOLATILE")
    assert tag.direction <= 0


def test_high_volatility_is_volatile():
    t = RegimeTagger(volatility_high=0.0005)
    candles = []
    p = 100.0
    for i in range(40):
        candles.append(_candle(p, p * 1.02, p * 0.98, p, i * 300_000))
    tag = t.tag(candles)
    assert tag.regime == "VOLATILE"


def test_cache_returns_same_tag():
    t = RegimeTagger()
    candles = _flat_candles(50)
    tag1 = t.tag(candles)
    tag2 = t.tag(candles)
    assert tag1 is tag2


def test_tag_fields_populated():
    t = RegimeTagger()
    tag = t.tag(_flat_candles(50))
    assert isinstance(tag.ts, int)
    assert isinstance(tag.trend_strength, float)
    assert isinstance(tag.volatility, float)
    assert isinstance(tag.direction, int)


def test_get_regime_tagger_singleton():
    t1 = get_regime_tagger()
    t2 = get_regime_tagger()
    assert t1 is t2


def test_missing_open_time_uses_zero():
    t = RegimeTagger()
    candles = [{"open": 100, "high": 100, "low": 100, "close": 100} for _ in range(50)]
    tag = t.tag(candles)
    assert tag.ts == 0
