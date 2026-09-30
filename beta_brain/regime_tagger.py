"""Regime Tagger - ported from HFT_Brain.

Classifies each candle's market regime for BTC 5m.
Standalone - no dependencies on other beta_brain modules.
"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class RegimeTag:
    ts: int
    regime: str
    trend_strength: float
    volatility: float
    direction: int


class RegimeTagger:
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        atr_period: int = 14,
        momentum_lookback: int = 10,
        volatility_low: float = 0.0003,
        volatility_high: float = 0.0020,
        trend_threshold: float = 0.0008,
        momentum_threshold: float = 0.0025,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.atr_period = atr_period
        self.momentum_lookback = momentum_lookback
        self.volatility_low = volatility_low
        self.volatility_high = volatility_high
        self.trend_threshold = trend_threshold
        self.momentum_threshold = momentum_threshold
        self._cache: Dict[int, RegimeTag] = {}

    def _ema(self, values: List[float], period: int) -> float:
        if len(values) < period:
            return sum(values) / len(values) if values else 0
        k = 2.0 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return ema

    def _atr(self, candles: List[dict], period: int) -> float:
        if len(candles) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h = candles[-i]["high"]
            l = candles[-i]["low"]
            pc = candles[-i - 1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        return sum(trs) / len(trs)

    def tag(self, candles: List[dict]) -> RegimeTag:
        if not candles or len(candles) < self.ema_slow + 2:
            return RegimeTag(
                ts=candles[-1].get("open_time", 0) if candles else 0,
                regime="UNKNOWN", trend_strength=0.0,
                volatility=0.0, direction=0,
            )
        ts = candles[-1].get("open_time", 0)
        if ts in self._cache:
            return self._cache[ts]

        closes = [c["close"] for c in candles]
        price = closes[-1]
        ema_f = self._ema(closes[-50:], self.ema_fast)
        ema_s = self._ema(closes[-50:], self.ema_slow)
        trend_strength = abs(ema_f - ema_s) / price if price > 0 else 0.0

        if len(closes) > self.momentum_lookback:
            past = closes[-self.momentum_lookback]
            momentum = (price - past) / past if past > 0 else 0.0
        else:
            momentum = 0.0

        ema_dir = 0
        if ema_f > ema_s * (1 + self.trend_threshold):
            ema_dir = 1
        elif ema_f < ema_s * (1 - self.trend_threshold):
            ema_dir = -1

        mom_dir = 0
        if momentum > self.momentum_threshold:
            mom_dir = 1
        elif momentum < -self.momentum_threshold:
            mom_dir = -1

        if ema_dir == 1 and mom_dir == 1:
            direction = 1
        elif ema_dir == -1 and mom_dir == -1:
            direction = -1
        else:
            direction = 0

        atr = self._atr(candles, self.atr_period)
        volatility = atr / price if price > 0 else 0.0

        if volatility >= self.volatility_high:
            regime = "VOLATILE"
        elif volatility < self.volatility_low:
            regime = "CHOPPY"
        elif direction == 1:
            regime = "TRENDING_UP"
        elif direction == -1:
            regime = "TRENDING_DOWN"
        else:
            regime = "RANGING"

        tag = RegimeTag(
            ts=ts, regime=regime,
            trend_strength=round(trend_strength, 6),
            volatility=round(volatility, 6),
            direction=direction,
        )
        self._cache[ts] = tag
        return tag


_tagger = None


def get_regime_tagger() -> RegimeTagger:
    global _tagger
    if _tagger is None:
        _tagger = RegimeTagger()
    return _tagger
