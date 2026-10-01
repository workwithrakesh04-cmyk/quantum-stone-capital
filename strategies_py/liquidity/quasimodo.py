"""Quasimodo (QM) - QM top (bearish) or QM bottom (bullish) pattern."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class QuasimodoStrategy(BaseStrategy):
    NAME = "quasimodo"
    BOOK_ID = "book_62"
    CATEGORY = "pattern"
    TIMEFRAMES = ["5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 10:
            return self._hold_signal("not enough candles")

        recent = candles[-10:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        curr = recent[-1]

        prior_low = min(lows[:5])
        later_low = min(lows[5:9])

        if later_low > prior_low and curr["low"] < later_low and self._is_bullish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.70,
                weight=self._get_rule_weight("long", "quasimodo"),
                reason="Bullish Quasimodo (swept higher low)",
                confluences=["quasimodo", "liquidity_sweep"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        prior_high = max(highs[:5])
        later_high = max(highs[5:9])

        if later_high < prior_high and curr["high"] > later_high and self._is_bearish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.70,
                weight=self._get_rule_weight("short", "quasimodo"),
                reason="Bearish Quasimodo (swept lower high)",
                confluences=["quasimodo", "liquidity_sweep"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no Quasimodo pattern")
