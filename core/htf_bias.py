"""HTF Bias - computes higher-timeframe trend from swing structure.

Uses the last N swing highs/lows:
  - Higher Highs + Higher Lows = BULLISH
  - Lower Highs + Lower Lows  = BEARISH
  - Mixed                     = NEUTRAL

Backtest mode: resamples LTF candles to a coarser timeframe (e.g., 5m -> 30m).
Live mode: could use actual HTF candles (not yet wired).

Usage:
    from core.htf_bias import HTFBias, compute_htf_bias, resample_candles
    bias = compute_htf_bias(candles_5m, htf_factor=6)
    if bias.is_bullish: ...
"""
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


@dataclass
class HTFBias:
    direction: str          # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: float       # 0.0 - 1.0
    last_hh: Optional[float] = None
    last_hl: Optional[float] = None
    last_lh: Optional[float] = None
    last_ll: Optional[float] = None

    @property
    def is_bullish(self) -> bool:
        return self.direction == "BULLISH"

    @property
    def is_bearish(self) -> bool:
        return self.direction == "BEARISH"

    @property
    def is_neutral(self) -> bool:
        return self.direction == "NEUTRAL"

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "last_hh": self.last_hh,
            "last_hl": self.last_hl,
            "last_lh": self.last_lh,
            "last_ll": self.last_ll,
        }


def resample_candles(candles: List[dict], factor: int) -> List[dict]:
    """Aggregate N consecutive candles into one coarser candle.

    factor=6 turns 5m into 30m. Uses chunked grouping (not time-aligned
    but fine for bias detection).
    """
    if factor <= 1:
        return list(candles)
    out = []
    n = len(candles)
    i = 0
    while i + factor <= n:
        chunk = candles[i:i + factor]
        out.append({
            "open": float(chunk[0]["open"]),
            "high": float(max(c["high"] for c in chunk)),
            "low": float(min(c["low"] for c in chunk)),
            "close": float(chunk[-1]["close"]),
            "volume": float(sum(c.get("volume", 0.0) for c in chunk)),
            "open_time": int(chunk[0].get("open_time", 0)),
            "buy_volume": 0.0,
            "sell_volume": 0.0,
        })
        i += factor
    return out


def _find_swings(candles: List[dict], lookback: int = 3) -> List[dict]:
    """Detect swing highs/lows using N-bar fractal.

    Falls back to window extremes when no strict fractals exist
    (e.g., in a purely monotonic ramp).

    Returns list of {type: 'H'|'L', idx, price} sorted by idx.
    """
    swings = []
    n = len(candles)
    if n < 2 * lookback + 1:
        return swings

    for i in range(lookback, n - lookback):
        is_high = all(candles[i]["high"] >= candles[i - j]["high"] for j in range(1, lookback + 1)) and \
                  all(candles[i]["high"] >= candles[i + j]["high"] for j in range(1, lookback + 1))
        is_low = all(candles[i]["low"] <= candles[i - j]["low"] for j in range(1, lookback + 1)) and \
                 all(candles[i]["low"] <= candles[i + j]["low"] for j in range(1, lookback + 1))
        if is_high:
            swings.append({"type": "H", "idx": i, "price": float(candles[i]["high"])})
        elif is_low:
            swings.append({"type": "L", "idx": i, "price": float(candles[i]["low"])})

    # Fallback: if fewer than 2 of each type, use window extremes
    n_h = sum(1 for s in swings if s["type"] == "H")
    n_l = sum(1 for s in swings if s["type"] == "L")
    if n_h < 2 or n_l < 2:
        # Walk backwards in windows of `lookback * 2` and record the
        # max-high and min-low of each window. Enough to infer trend.
        window = max(lookback * 2, 10)
        starts = list(range(0, n - window, window))
        fallback = []
        for s in starts:
            chunk = candles[s:s + window]
            hi_idx = max(range(len(chunk)), key=lambda j: chunk[j]["high"])
            lo_idx = min(range(len(chunk)), key=lambda j: chunk[j]["low"])
            fallback.append({"type": "H", "idx": s + hi_idx, "price": float(chunk[hi_idx]["high"])})
            fallback.append({"type": "L", "idx": s + lo_idx, "price": float(chunk[lo_idx]["low"])})
        # Combine and dedupe (prefer real fractals, add fallback for missing types)
        existing_idx_types = {(s["idx"], s["type"]) for s in swings}
        for f in fallback:
            if (f["idx"], f["type"]) not in existing_idx_types:
                swings.append(f)
        swings.sort(key=lambda s: s["idx"])

    return swings


def compute_htf_bias(candles: List[dict], htf_factor: int = 6,
                    lookback: int = 3, min_swings: int = 4) -> HTFBias:
    """Compute HTF bias from LTF candles by resampling.

    Args:
        candles: LTF candles (e.g., 5m).
        htf_factor: resample factor. 6 -> 30m, 12 -> 1h, 48 -> 4h.
        lookback: bars on each side to confirm a swing.
        min_swings: minimum swings required to make a call.

    Returns:
        HTFBias with direction, confidence, and the last four swing prices.
    """
    if len(candles) < htf_factor * 10:
        return HTFBias(direction="NEUTRAL", confidence=0.0)

    htf = resample_candles(candles, htf_factor)
    if len(htf) < 10:
        return HTFBias(direction="NEUTRAL", confidence=0.0)

    swings = _find_swings(htf, lookback=lookback)
    if len(swings) < min_swings:
        return HTFBias(direction="NEUTRAL", confidence=0.0)

    # Take last 4 swings of each type (or as many as we have)
    highs = [s for s in swings if s["type"] == "H"][-4:]
    lows = [s for s in swings if s["type"] == "L"][-4:]

    last_hh = highs[-1]["price"] if highs else None
    last_lh = highs[-2]["price"] if len(highs) >= 2 else None
    last_ll = lows[-1]["price"] if lows else None
    last_hl = lows[-2]["price"] if len(lows) >= 2 else None

    # Bullish: recent H > prior H AND recent L > prior L
    bullish_h = len(highs) >= 2 and highs[-1]["price"] > highs[-2]["price"]
    bullish_l = len(lows) >= 2 and lows[-1]["price"] > lows[-2]["price"]
    bearish_h = len(highs) >= 2 and highs[-1]["price"] < highs[-2]["price"]
    bearish_l = len(lows) >= 2 and lows[-1]["price"] < lows[-2]["price"]

    # Score
    bull_score = (1 if bullish_h else 0) + (1 if bullish_l else 0)
    bear_score = (1 if bearish_h else 0) + (1 if bearish_l else 0)

    if bull_score == 2 and bear_score == 0:
        direction = "BULLISH"
        # Confidence: also check consistency over 3 highs and 3 lows
        conf = 0.5
        if len(highs) >= 3 and highs[-1]["price"] > highs[-2]["price"] > highs[-3]["price"]:
            conf += 0.25
        if len(lows) >= 3 and lows[-1]["price"] > lows[-2]["price"] > lows[-3]["price"]:
            conf += 0.25
    elif bear_score == 2 and bull_score == 0:
        direction = "BEARISH"
        conf = 0.5
        if len(highs) >= 3 and highs[-1]["price"] < highs[-2]["price"] < highs[-3]["price"]:
            conf += 0.25
        if len(lows) >= 3 and lows[-1]["price"] < lows[-2]["price"] < lows[-3]["price"]:
            conf += 0.25
    else:
        direction = "NEUTRAL"
        conf = 0.0

    return HTFBias(
        direction=direction,
        confidence=round(min(conf, 1.0), 3),
        last_hh=last_hh, last_hl=last_hl,
        last_lh=last_lh, last_ll=last_ll,
    )
