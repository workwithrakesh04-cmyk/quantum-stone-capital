"""Tests for beta_brain.shadow_tracker."""
from dataclasses import dataclass
from beta_brain.shadow_tracker import ShadowTracker, ShadowTrade


@dataclass
class FakeSignal:
    strategy: str = "foo"
    direction: str = "LONG"


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def _series(n, base=100.0, ts_step=300_000):
    """Return n candles with real high/low ranges so ATR > 0."""
    out = []
    for i in range(n):
        o = base
        h = base * 1.005
        l = base * 0.995
        c = base
        out.append(_candle(o, h, l, c, i * ts_step))
    return out


def test_empty_tracker():
    st = ShadowTracker()
    r = st.report()
    assert r["open_count"] == 0
    assert r["closed_count"] == 0


def test_record_signals_creates_open_trades():
    st = ShadowTracker()
    st.record_signals([FakeSignal("foo", "LONG")], _series(20), "RANGING")
    assert len(st.open_trades) == 1


def test_hold_signals_ignored():
    st = ShadowTracker()
    st.record_signals([FakeSignal("foo", "HOLD")], _series(20), "RANGING")
    assert len(st.open_trades) == 0


def test_long_tp_hit():
    st = ShadowTracker(rr=1.0, atr_mult=0.5)
    candles = _series(20, 100.0)
    st.record_signals([FakeSignal("foo", "LONG")], candles, "RANGING")
    assert len(st.open_trades) == 1
    st.process_candle(_candle(100, 200, 100, 200, 99999))
    assert len(st.closed_trades) == 1
    assert st.closed_trades[0].outcome == "WIN"


def test_long_sl_hit():
    st = ShadowTracker(rr=1.0, atr_mult=0.5)
    candles = _series(20, 100.0)
    st.record_signals([FakeSignal("foo", "LONG")], candles, "RANGING")
    st.process_candle(_candle(100, 100, 10, 10, 99999))
    assert len(st.closed_trades) == 1
    assert st.closed_trades[0].outcome == "LOSS"


def test_timeout_after_12_bars():
    st = ShadowTracker(rr=10.0, atr_mult=0.5)
    candles = _series(20, 100.0)
    st.record_signals([FakeSignal("foo", "LONG")], candles, "RANGING")
    for _ in range(12):
        st.process_candle(_candle(100, 100.1, 99.9, 100, 99999))
    assert len(st.closed_trades) == 1
    assert st.closed_trades[0].outcome == "TIMEOUT"


def test_regime_stats_populated():
    st = ShadowTracker(rr=1.0, atr_mult=0.5)
    st.record_signals([FakeSignal("foo", "LONG")], _series(20, 100.0), "TRENDING_UP")
    st.process_candle(_candle(100, 200, 100, 200, 99999))
    r = st.report()
    assert "TRENDING_UP" in r["regimes"]


def test_signal_stats_populated():
    st = ShadowTracker(rr=1.0, atr_mult=0.5)
    st.record_signals([FakeSignal("foo", "LONG")], _series(20, 100.0), "RANGING")
    st.process_candle(_candle(100, 200, 100, 200, 99999))
    r = st.report()
    assert "foo" in r["strategies"]


def test_no_atr_skips_recording():
    st = ShadowTracker()
    st.record_signals([FakeSignal("foo", "LONG")], [], "RANGING")
    assert len(st.open_trades) == 0


def test_multiple_signals_recorded():
    st = ShadowTracker()
    sigs = [FakeSignal(f"strat{i}", "LONG") for i in range(3)]
    st.record_signals(sigs, _series(20, 100.0), "RANGING")
    assert len(st.open_trades) == 3


def test_short_tp_hit():
    st = ShadowTracker(rr=1.0, atr_mult=0.5)
    st.record_signals([FakeSignal("foo", "SHORT")], _series(20, 100.0), "RANGING")
    assert len(st.open_trades) == 1
    st.process_candle(_candle(100, 100, 10, 10, 99999))
    assert len(st.closed_trades) == 1
    assert st.closed_trades[0].outcome == "WIN"
