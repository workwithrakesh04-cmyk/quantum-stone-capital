"""AI Trend Flow - flow-feature based trend classifier."""
from typing import List
from collections import deque
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class AITrendFlowStrategy(BaseStrategy):
    NAME = "ai_trend_flow"
    BOOK_ID = "zeiierman_ai_trend_flow"
    CATEGORY = "ml_flow"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MEMORY_DEPTH = 300
    K_NEIGHBORS = 9
    ATR_LEN = 14
    MIN_DRIVE = 0.45
    MIN_ANALOG = 0.40
    MIN_BANK = 40
    COOLDOWN_BARS = 5
    WARMUP_BARS = 150

    def __init__(self, timeframe: str = "5m"):
        super().__init__(timeframe)
        self._bank = deque(maxlen=self.MEMORY_DEPTH)
        self._bar_count = 0
        self._last_fire_bar = -999
        self._last_dir = 0

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
        opens = np.array([c["open"] for c in candles])
        atr = self._atr(highs, lows, closes, self.ATR_LEN)
        if atr <= 0:
            return self._hold_signal("ATR is zero")

        i = len(closes) - 1
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        rng = max(h - l, 1e-9)
        body = (c - o) / rng
        clv = ((c - l) - (h - c)) / rng

        if self._bar_count < self.WARMUP_BARS:
            return self._hold_signal("warmup")
        if self._bar_count - self._last_fire_bar < self.COOLDOWN_BARS:
            return self._hold_signal("cooldown")

        curr = candles[-1]
        # Simplified: no k-NN bank — use flow features directly
        if body > 0.3 and clv > 0.2:
            self._last_fire_bar = self._bar_count
            self._last_dir = 1
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.62,
                weight=self._get_rule_weight("long", "trend"),
                reason=f"AI Flow LONG (body={body:.2f} clv={clv:.2f})",
                confluences=["ai_flow"],
                timeframe=self.timeframe,
                price=c, ts=curr.get("open_time", 0),
            )
        if body < -0.3 and clv < -0.2:
            self._last_fire_bar = self._bar_count
            self._last_dir = -1
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.62,
                weight=self._get_rule_weight("short", "trend"),
                reason=f"AI Flow SHORT (body={body:.2f} clv={clv:.2f})",
                confluences=["ai_flow"],
                timeframe=self.timeframe,
                price=c, ts=curr.get("open_time", 0),
            )
        return self._hold_signal("no signal")
