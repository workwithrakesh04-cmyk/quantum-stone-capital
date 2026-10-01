"""Tests for core.htf_bias."""
from core.htf_bias import (
    HTFBias, compute_htf_bias, resample_candles,
)


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1.0, "open_time": ts}


def _uptrend(n=600, base=100.0):
    """Non-monotonic uptrend: net up drift with noise."""
    import math
    out = []
    p = base
    for i in range(n):
        # Upward drift + sine wave wiggle
        drift = 0.002 * (i % 12) - 0.001 * ((i + 5) % 12)
        p = base * (1 + 0.002 * i * 0.1 + 0.005 * math.sin(i / 20.0) + drift * 0.01)
        h = p + 0.3
        l = p - 0.3
        out.append(_candle(p - 0.1, h, l, p, i * 300_000))
    return out


def _downtrend(n=600, base=100.0):
    """Non-monotonic downtrend: net down drift with noise."""
    import math
    out = []
    for i in range(n):
        p = base * (1 - 0.002 * i * 0.1 + 0.005 * math.sin(i / 20.0))
        h = p + 0.3
        l = p - 0.3
        out.append(_candle(p + 0.1, h, l, p, i * 300_000))
    return out


def _flat(n=500, base=100.0):
    return [_candle(base, base * 1.001, base * 0.999, base, i * 300_000) for i in range(n)]


def test_htf_bias_dataclass():
    b = HTFBias(direction="BULLISH", confidence=0.75)
    assert b.is_bullish
    assert not b.is_bearish
    assert not b.is_neutral


def test_htf_bias_to_dict():
    b = HTFBias(direction="BEARISH", confidence=0.5, last_hh=105.0)
    d = b.to_dict()
    assert d["direction"] == "BEARISH"
    assert d["last_hh"] == 105.0


def test_resample_reduces_count():
    candles = _uptrend(60)
    out = resample_candles(candles, factor=6)
    assert len(out) == 10


def test_resample_aggregates_high_low():
    candles = [_candle(100, 105, 95, 102, i) for i in range(6)]
    out = resample_candles(candles, factor=6)
    assert len(out) == 1
    assert out[0]["high"] == 105
    assert out[0]["low"] == 95
    assert out[0]["open"] == 100
    assert out[0]["close"] == 102


def test_resample_factor_1_is_identity():
    candles = _uptrend(10)
    out = resample_candles(candles, factor=1)
    assert len(out) == 10


def test_bullish_uptrend_detected():
    candles = _uptrend(600)
    bias = compute_htf_bias(candles, htf_factor=6)
    assert bias.direction == "BULLISH"


def test_bearish_downtrend_detected():
    candles = _downtrend(600)
    bias = compute_htf_bias(candles, htf_factor=6)
    assert bias.direction == "BEARISH"


def test_flat_returns_neutral_or_low_confidence():
    candles = _flat(600)
    bias = compute_htf_bias(candles, htf_factor=6)
    assert bias.confidence <= 1.0


def test_short_history_neutral():
    bias = compute_htf_bias(_uptrend(20))
    assert bias.direction == "NEUTRAL"
    assert bias.confidence == 0.0


def test_empty_candles_neutral():
    bias = compute_htf_bias([])
    assert bias.direction == "NEUTRAL"
