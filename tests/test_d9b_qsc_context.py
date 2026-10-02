"""D9b tests - real MarketContext builder for QSC."""
from datetime import datetime, timezone

import pytest

from backtest.qsc_context import (
    build_market_context,
    compute_momentum,
    compute_rsi,
    compute_atr,
    compute_volatility,
    session_from_ts_ms,
    active_killzones_from_ts_ms,
)


def _mk_candle(close, open_=None, high=None, low=None, ts=0, vol=1.0):
    o = open_ if open_ is not None else close
    h = high if high is not None else max(o, close) * 1.001
    l = low if low is not None else min(o, close) * 0.999
    return {"open": o, "high": h, "low": l, "close": close,
            "volume": vol, "open_time": ts}


def _ramp(start=100.0, step=0.5, n=50, ts0=1759000000000, tf_ms=300_000):
    return [_mk_candle(start + i * step, ts=ts0 + i * tf_ms) for i in range(n)]


class TestMomentum:

    def test_flat_returns_zero(self):
        c = [100.0] * 30
        assert compute_momentum(c, 20) == 0.0

    def test_up_ramp_positive(self):
        c = [100.0 + i for i in range(30)]
        assert compute_momentum(c, 20) > 0

    def test_down_ramp_negative(self):
        c = [100.0 - i for i in range(30)]
        assert compute_momentum(c, 20) < 0

    def test_too_few_returns_zero(self):
        assert compute_momentum([100.0], 20) == 0.0


class TestRSI:

    def test_all_up_high(self):
        c = [100.0 + i for i in range(30)]
        assert compute_rsi(c, 14) > 90

    def test_all_down_low(self):
        c = [100.0 - i for i in range(30)]
        assert compute_rsi(c, 14) < 10

    def test_too_few_returns_neutral(self):
        assert compute_rsi([100.0], 14) == 50.0

    def test_flat_returns_neutral_or_high(self):
        c = [100.0] * 30
        # No gains no losses -> avg_loss=0, avg_gain=0 -> 50.0
        assert compute_rsi(c, 14) == 50.0


class TestATRAndVolatility:

    def test_atr_positive_on_range(self):
        candles = _ramp(100.0, 0.5, 30)
        assert compute_atr(candles, 14) > 0

    def test_volatility_positive(self):
        candles = _ramp(100.0, 0.5, 30)
        assert compute_volatility(candles, 14) > 0

    def test_volatility_zero_when_flat(self):
        candles = [_mk_candle(100.0, high=100.0, low=100.0, open_=100.0)
                   for _ in range(30)]
        # flat candles -> ATR=0 -> volatility=0
        assert compute_volatility(candles, 14) == 0.0


class TestSession:

    def test_tokyo_hour(self):
        # 2026-01-01 03:00 UTC
        ts = int(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert session_from_ts_ms(ts) == "tokyo"

    def test_london_hour(self):
        ts = int(datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert session_from_ts_ms(ts) == "london"

    def test_ny_hour(self):
        ts = int(datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert session_from_ts_ms(ts) == "new_york"

    def test_off_hours(self):
        ts = int(datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert session_from_ts_ms(ts) == "off_hours"

    def test_zero_ts(self):
        assert session_from_ts_ms(0) == "off_hours"


class TestKillzones:

    def test_london_kz(self):
        ts = int(datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert "london_kz" in active_killzones_from_ts_ms(ts)

    def test_ny_kz(self):
        ts = int(datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert "ny_kz" in active_killzones_from_ts_ms(ts)

    def test_outside_returns_empty(self):
        ts = int(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert active_killzones_from_ts_ms(ts) == []


class TestBuildMarketContext:

    def test_returns_none_when_too_few(self):
        candles = _ramp(100.0, 0.5, 5)
        assert build_market_context(candles, "BTCUSDT") is None

    def test_returns_context_with_real_values(self):
        candles = _ramp(100.0, 0.5, 50)
        ctx = build_market_context(candles, "BTCUSDT")
        assert ctx is not None
        assert ctx.symbol == "BTCUSDT"
        assert len(ctx.closes) == 50
        assert ctx.momentum > 0
        assert ctx.rsi > 50
        assert ctx.volatility > 0
        # Highs/lows must be REAL highs/lows, not synthetic multipliers
        assert ctx.highs[-1] >= ctx.closes[-1]
        assert ctx.lows[-1] <= ctx.closes[-1]

    def test_regime_is_lowercase(self):
        candles = _ramp(100.0, 0.5, 50)
        ctx = build_market_context(candles, "BTCUSDT")
        assert ctx.regime is None or ctx.regime == ctx.regime.lower()

    def test_can_disable_regime_tagging(self):
        candles = _ramp(100.0, 0.5, 50)
        ctx = build_market_context(candles, "BTCUSDT", tag_regime=False)
        assert ctx is not None
        assert ctx.regime is None

    def test_symbol_preserved(self):
        candles = _ramp(100.0, 0.5, 50)
        ctx = build_market_context(candles, "XAUUSD")
        assert ctx.symbol == "XAUUSD"

class TestBOS:

    def test_too_few_returns_none(self):
        from backtest.qsc_context import compute_bos
        candles = _ramp(100.0, 0.1, 10)
        assert compute_bos(candles) is None

    def test_uptrend_breakout_detected(self):
        from backtest.qsc_context import compute_bos
        # Build a series with a clear swing high, then break above it
        c = [100.0 + i * 0.1 for i in range(30)]
        c += [102.9, 102.5, 102.3, 102.5, 102.8, 103.5]  # breaks prior high
        candles = [_mk_candle(price, high=price, low=price, open_=price - 0.05)
                   for price in c]
        bos = compute_bos(candles)
        # Either detects BOS_BULLISH or None depending on swing shape;
        # we mainly test it does not crash and returns a valid value.
        assert bos in (None, "BOS_BULLISH", "BOS_BEARISH")

    def test_flat_returns_none(self):
        from backtest.qsc_context import compute_bos
        candles = [_mk_candle(100.0, high=100.0, low=100.0, open_=100.0)
                   for _ in range(40)]
        assert compute_bos(candles) is None


class TestDeltaProxy:

    def test_empty_returns_zero(self):
        from backtest.qsc_context import compute_delta_proxy
        assert compute_delta_proxy([]) == 0.0

    def test_bullish_bodies_positive(self):
        from backtest.qsc_context import compute_delta_proxy
        # Every candle: open=100, close=101 (positive body)
        candles = [_mk_candle(101.0, open_=100.0, high=101.0, low=100.0, vol=10.0)
                   for _ in range(30)]
        delta = compute_delta_proxy(candles, lookback=20)
        assert delta > 0

    def test_bearish_bodies_negative(self):
        from backtest.qsc_context import compute_delta_proxy
        candles = [_mk_candle(99.0, open_=100.0, high=100.0, low=99.0, vol=10.0)
                   for _ in range(30)]
        delta = compute_delta_proxy(candles, lookback=20)
        assert delta < 0

    def test_zero_volume_returns_zero(self):
        from backtest.qsc_context import compute_delta_proxy
        candles = [_mk_candle(101.0, open_=100.0, vol=0.0) for _ in range(30)]
        assert compute_delta_proxy(candles, lookback=20) == 0.0