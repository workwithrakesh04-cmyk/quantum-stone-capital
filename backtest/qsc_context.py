"""Real MarketContext builder for QSC backtesting and D9a demo.

QSC's MainBrainV2.run() expects a MarketContext that already has
momentum, rsi, volatility, regime, and session pre-computed. The
live runner (scripts/run_hybrid.py) has historically fed it fake
values (hardcoded RSI=50, regime derived from a 20-bar momentum
sign, synthetic highs/lows). This module does it properly from
real OHLCV candles.

Used by:
  - backtest/qsc_backtester.py (D9b)
  - scripts/run_demo.py (D9a, later)
"""
import math
from datetime import datetime, timezone
from typing import List, Optional

from core.market_context import MarketContext
from beta_brain.regime_tagger import get_regime_tagger


# ----------------------------------------------------------------------
# Feature calculations
# ----------------------------------------------------------------------

def _closes(candles: List[dict]) -> List[float]:
    return [float(c["close"]) for c in candles]


def compute_momentum(closes: List[float], lookback: int = 20) -> float:
    if len(closes) < lookback + 1 or closes[-lookback - 1] == 0:
        return 0.0
    return (closes[-1] - closes[-lookback - 1]) / closes[-lookback - 1]


def compute_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses += -change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_atr(candles: List[dict], period: int = 14) -> float:
    """Average True Range over the last `period` candles."""
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i]["high"])
        l = float(candles[i]["low"])
        pc = float(candles[i - 1]["close"])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if not trs:
        return 0.0
    recent = trs[-period:] if len(trs) >= period else trs
    return sum(recent) / len(recent)


def compute_volatility(candles: List[dict], period: int = 14) -> float:
    """ATR / close - a dimensionless volatility measure."""
    if not candles:
        return 0.0
    atr = compute_atr(candles, period)
    last_close = float(candles[-1]["close"])
    if last_close <= 0:
        return 0.0
    return atr / last_close


def _swing_highs_lows(candles: List[dict], left: int = 5, right: int = 5):
    """Return (swing_highs, swing_lows) as lists of (index, price).

    A swing high at index i requires candle[i].high > all of the
    `left` candles before and the `right` candles after.
    """
    highs = []
    lows = []
    n = len(candles)
    if n < left + right + 1:
        return highs, lows
    for i in range(left, n - right):
        h = float(candles[i]["high"])
        l = float(candles[i]["low"])
        is_high = all(h >= float(candles[j]["high"]) for j in range(i - left, i)) \
            and all(h >= float(candles[j]["high"]) for j in range(i + 1, i + 1 + right))
        is_low = all(l <= float(candles[j]["low"]) for j in range(i - left, i)) \
            and all(l <= float(candles[j]["low"]) for j in range(i + 1, i + 1 + right))
        if is_high:
            highs.append((i, h))
        if is_low:
            lows.append((i, l))
    return highs, lows


def compute_bos(candles: List[dict], left: int = 5, right: int = 5) -> Optional[str]:
    """Detect the most recent Break of Structure (BOS) or Change of
    Character (CHoCH).

    Simplified: compare the last two swing highs and last two swing
    lows. If the latest close has broken above the most recent swing
    high -> "BOS_BULLISH". If below the most recent swing low ->
    "BOS_BEARISH". If we broke the opposite side after a trend ->
    "CHOCH_*". Otherwise None.
    """
    if len(candles) < 15:
        return None
    highs, lows = _swing_highs_lows(candles, left=left, right=right)
    if not highs and not lows:
        return None
    last_close = float(candles[-1]["close"])
    last_high = highs[-1][1] if highs else None
    last_low = lows[-1][1] if lows else None
    if last_high is not None and last_close > last_high:
        return "BOS_BULLISH"
    if last_low is not None and last_close < last_low:
        return "BOS_BEARISH"
    return None


def compute_delta_proxy(candles: List[dict], lookback: int = 20) -> float:
    """Volume-weighted candle-body delta proxy.

    For each of the last `lookback` candles, weight the body
    (close - open) by the candle's volume. Sum and normalise.

    Positive = buying pressure, negative = selling pressure.
    This is NOT true order-flow delta; it is a cheap proxy that
    captures directional bias when tick data is unavailable.
    """
    if not candles:
        return 0.0
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    total_vol = 0.0
    weighted = 0.0
    for c in recent:
        o = float(c["open"])
        cl = float(c["close"])
        v = float(c.get("volume", 0.0))
        weighted += (cl - o) * v
        total_vol += v
    if total_vol <= 0:
        return 0.0
    return weighted / total_vol


def session_from_ts_ms(ts_ms: int) -> str:
    """Map a UTC millisecond timestamp to a session label."""
    if ts_ms <= 0:
        return "off_hours"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    h = dt.hour
    if 0 <= h < 7:
        return "tokyo"
    if 7 <= h < 12:
        return "london"
    if 12 <= h < 21:
        return "new_york"
    return "off_hours"


def active_killzones_from_ts_ms(ts_ms: int) -> List[str]:
    """Return any killzones active at the given UTC millisecond time."""
    if ts_ms <= 0:
        return []
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    h = dt.hour
    kz = []
    # London killzone 07:00-10:00 UTC
    if 7 <= h < 10:
        kz.append("london_kz")
    # NY killzone 12:00-15:00 UTC
    if 12 <= h < 15:
        kz.append("ny_kz")
    return kz


# ----------------------------------------------------------------------
# Context builder
# ----------------------------------------------------------------------

_tagger_singleton = None


def _get_tagger():
    global _tagger_singleton
    if _tagger_singleton is None:
        _tagger_singleton = get_regime_tagger()
    return _tagger_singleton


def build_market_context(
    candles: List[dict],
    symbol: str,
    timeframe: str = "5m",
    tag_regime: bool = True,
    min_bars: int = 20,
) -> Optional[MarketContext]:
    """Build a real MarketContext from a window of OHLCV candles.

    Returns None if there are too few candles to compute features.
    """
    if not candles or len(candles) < min_bars:
        return None

    closes = _closes(candles)
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    volumes = [float(c.get("volume", 0.0)) for c in candles]

    last_ts_ms = int(candles[-1].get("open_time", 0))
    momentum = compute_momentum(closes, lookback=20)
    rsi = compute_rsi(closes, period=14)
    volatility = compute_volatility(candles, period=14)
    bos = compute_bos(candles)
    delta = compute_delta_proxy(candles, lookback=20)
    session = session_from_ts_ms(last_ts_ms)
    killzones = active_killzones_from_ts_ms(last_ts_ms)

    regime: Optional[str] = None
    if tag_regime:
        try:
            tag = _get_tagger().tag(candles)
            regime = getattr(tag, "regime", None)
        except Exception:
            regime = None

    # QSC's selector expects lowercase regime strings
    # ("trending_up" | "trending_down" | "ranging" | "volatile").
    # Beta's tagger returns uppercase ("RANGING" | "VOLATILE" | ...).
    # Normalise.
    if regime:
        regime = regime.lower().replace(" ", "_")

    return MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=(
            datetime.fromtimestamp(last_ts_ms / 1000, tz=timezone.utc).isoformat()
            if last_ts_ms > 0 else None
        ),
        closes=closes,
        highs=highs,
        lows=lows,
        opens=opens,
        volumes=volumes,
        momentum=momentum,
        rsi=rsi,
        delta=delta,
        volatility=volatility,
        bos=bos,
        regime=regime,
        session=session,
        active_killzones=killzones,
        is_weekend=False,    # crypto
        is_illiquid=False,
        kyle_lambda=None,
        passes_filter=False, # set by MainBrainV2.run via signal_filter
        signal_score=0.0,
        agreeing_frameworks=["binance"],
        harmonic_bullish=False,
        harmonic_bearish=False,
        wave3_active=False,
        wave_c_active=False,
        meta={"source": "qsc_context", "n_candles": len(candles)},
    )