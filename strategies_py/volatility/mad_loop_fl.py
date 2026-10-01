"""MAD Loop FL - for-loop trend score."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class MADForLoopStrategy(BaseStrategy):
    NAME = "mad_fl"
    BOOK_ID = "lyrors_mad_loop"
    CATEGORY = "trend_momentum"
    TIMEFRAMES = ["5m", "15m", "1h"]
    LOOP_A = 10
    LOOP_B = 60
    THRESHOLD_LONG = 23
    THRESHOLD_SHORT = 3

    def _loop_score(self, closes, a, b):
        if len(closes) < b + 1:
            return 0
        curr = closes[-1]
        score = 0
        for i in range(a, b + 1):
            score += 1 if curr > closes[-1 - i] else -1
        return score

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.LOOP_B + 5:
            return self._hold_signal("not enough candles")
        closes = np.array([c["close"] for c in candles])

        score_now = self._loop_score(closes, self.LOOP_A, self.LOOP_B)
        score_prev = self._loop_score(closes[:-1], self.LOOP_A, self.LOOP_B)
        curr = candles[-1]

        if score_prev <= self.THRESHOLD_LONG and score_now > self.THRESHOLD_LONG:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.72,
                weight=self._get_rule_weight("long", "trend"),
                reason=f"MAD FL LONG (score={score_now})",
                confluences=["for_loop_trend"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        if score_prev >= self.THRESHOLD_SHORT and score_now < self.THRESHOLD_SHORT:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.72,
                weight=self._get_rule_weight("short", "trend"),
                reason=f"MAD FL SHORT (score={score_now})",
                confluences=["for_loop_trend"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        return self._hold_signal(f"score={score_now}")
