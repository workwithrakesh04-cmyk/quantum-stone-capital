"""ML Momentum - multi-horizon ROC classifier."""
from typing import List
from collections import deque
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class MLMomentumStrategy(BaseStrategy):
    NAME = "ml_momentum"
    BOOK_ID = "zeiierman_ml_momentum"
    CATEGORY = "ml_momentum"
    TIMEFRAMES = ["5m", "15m", "1h"]
    ATR_LEN = 14
    WARMUP_BARS = 150
    COOLDOWN_BARS = 3

    def __init__(self, timeframe: str = "5m"):
        super().__init__(timeframe)
        self._bar_count = 0
        self._last_fire_bar = -999

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

        c = closes[-1]
        roc3 = (c / closes[-4] - 1.0) if closes[-4] > 0 else 0.0
        roc7 = (c / closes[-8] - 1.0) if closes[-8] > 0 else 0.0
        roc15 = (c / closes[-16] - 1.0) if closes[-16] > 0 else 0.0
        atr_pct = atr / c if c > 0 else 1e-6
        roc3_n = max(-1.0, min(1.0, roc3 / (3 * atr_pct + 1e-9)))
        roc7_n = max(-1.0, min(1.0, roc7 / (7 * atr_pct + 1e-9)))
        roc15_n = max(-1.0, min(1.0, roc15 / (15 * atr_pct + 1e-9)))
        align = (np.sign(roc3_n) + np.sign(roc7_n) + np.sign(roc15_n)) / 3.0

        if self._bar_count < self.WARMUP_BARS:
            return self._hold_signal("warmup")
        if self._bar_count - self._last_fire_bar < self.COOLDOWN_BARS:
            return self._hold_signal("cooldown")

        curr = candles[-1]
        if align > 0.5 and roc3_n > 0.2:
            self._last_fire_bar = self._bar_count
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.62,
                weight=self._get_rule_weight("long", "momentum"),
                reason=f"ML Mom LONG (align={align:.2f} roc3={roc3_n:.2f})",
                confluences=["ml_momentum"],
                timeframe=self.timeframe,
                price=c, ts=curr.get("open_time", 0),
            )
        if align < -0.5 and roc3_n < -0.2:
            self._last_fire_bar = self._bar_count
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.62,
                weight=self._get_rule_weight("short", "momentum"),
                reason=f"ML Mom SHORT (align={align:.2f} roc3={roc3_n:.2f})",
                confluences=["ml_momentum"],
                timeframe=self.timeframe,
                price=c, ts=curr.get("open_time", 0),
            )
        return self._hold_signal("no alignment")
