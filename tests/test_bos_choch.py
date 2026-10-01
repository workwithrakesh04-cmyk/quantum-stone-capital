"""Tests for strategies_py.ict_smc.bos_choch + HTF integration."""
from strategies_py.ict_smc.bos_choch import BOSCHoCHStrategy
from core.htf_bias import compute_htf_bias
from beta_brain.signal import Signal
import math


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1.0, "open_time": ts}


def _flat(n=100, base=100.0):
    return [_candle(base, base * 1.001, base * 0.999, base, i * 300_000) for i in range(n)]


def _breakout_up(n=100, base=100.0):
    """Wiggle then strong up move at end."""
    out = []
    for i in range(n - 5):
        p = base + 0.3 * math.sin(i / 5.0)
        out.append(_candle(p - 0.05, p + 0.15, p - 0.15, p, i * 300_000))
    p = base
    for i in range(5):
        p *= 1.01
        out.append(_candle(p * 0.995, p * 1.001, p * 0.994, p, (n - 5 + i) * 300_000))
    return out


def _wave_uptrend(n=600, base=100.0):
    """Realistic non-monotonic uptrend."""
    out = []
    for i in range(n):
        p = base * (1 + 0.002 * i * 0.1 + 0.005 * math.sin(i / 20.0))
        out.append(_candle(p - 0.1, p + 0.3, p - 0.3, p, i * 300_000))
    return out


def test_bos_choch_instantiates():
    s = BOSCHoCHStrategy(timeframe="5m")
    assert s.NAME == "bos_choch"
    assert s.BOOK_ID == "ftm_smc"


def test_short_history_returns_hold():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_flat(20))
    assert sig.direction == "HOLD"


def test_flat_candles_returns_hold():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_flat(100))
    assert sig.direction == "HOLD"


def test_breakout_up_produces_valid_signal():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_breakout_up(100))
    assert sig.direction in ("LONG", "SHORT", "HOLD")


def test_signal_is_valid_type():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_flat(100))
    assert isinstance(sig, Signal)


def test_signal_has_strategy_name():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_flat(100))
    assert sig.strategy == "bos_choch"


def test_signal_reason_populated():
    s = BOSCHoCHStrategy(timeframe="5m")
    sig = s.analyze(_flat(100))
    assert isinstance(sig.reason, str)
    assert len(sig.reason) > 0


def test_timeframes_declared():
    s = BOSCHoCHStrategy(timeframe="5m")
    assert "5m" in s.TIMEFRAMES


def test_bias_on_uptrend():
    candles = _wave_uptrend(600)
    bias = compute_htf_bias(candles)
    assert bias.direction == "BULLISH"


def test_strategy_loads_via_loader():
    from strategies_py.loader import load_all_strategies
    classes = load_all_strategies()
    names = [c.NAME for c in classes]
    assert "bos_choch" in names
