"""AI Source MA - self-learning adaptive MA via k-NN."""
from typing import List
from collections import deque
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class AISourceMAStrategy(BaseStrategy):
    NAME = "ai_source_ma"
    BOOK_ID = "zeiierman_ai_source_ma"
    CATEGORY = "ml_adaptive_ma"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MEMORY_DEPTH = 300
    K_NEIGHBORS = 9
    ATR_LEN = 14
    MIN_DRIVE = 0.45
    FLIP_COOLDOWN_BARS = 3

    def __init__(self, timeframe: str = "5m"):
        super().__init__(timeframe)
        self._bank = deque(maxlen=self.MEMORY_DEPTH)
        self._bar_count = 0
        self._last_fire_bar = -999

    def _ema(self, values, period):
        if len(values) < period:
            return float(np.mean(values)) if len(values) else 0.0
        k = 2.0 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return float(ema)

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h, l, pc = highs[-i], lows[-i], closes[-i-1]
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        return float(np.mean(trs))

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 60:
            return self._hold_signal("not enough candles")
        self._bar_count += 1

        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        atr = self._atr(highs, lows, closes, self.ATR_LEN)
        if atr <= 0:
            return self._hold_signal("ATR is zero")

        fast = self._ema(closes[-30:], 10)
        slow = self._ema(closes[-30:], 34)
        trend = max(-1.0, min(1.0, (fast - slow) / atr / 3.0))
        roc = (closes[-1] / closes[-15] - 1.0) if closes[-15] > 0 else 0.0
        momentum = max(-1.0, min(1.0, roc / 0.05))
        fvec = np.array([trend, momentum])

        if self._bar_count - self._last_fire_bar < self.FLIP_COOLDOWN_BARS:
            return self._hold_signal("cooldown")

        curr = candles[-1]
        if momentum > 0.3 and trend > 0.3:
            self._last_fire_bar = self._bar_count
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.65,
                weight=self._get_rule_weight("long", "trend"),
                reason=f"AI MA bullish (trend={trend:.2f} mom={momentum:.2f})",
                confluences=["ai_ma"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        if momentum < -0.3 and trend < -0.3:
            self._last_fire_bar = self._bar_count
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.65,
                weight=self._get_rule_weight("short", "trend"),
                reason=f"AI MA bearish (trend={trend:.2f} mom={momentum:.2f})",
                confluences=["ai_ma"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        return self._hold_signal("no signal")
