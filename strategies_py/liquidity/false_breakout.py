"""False Breakout - prior range broken then reversed."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class FalseBreakoutStrategy(BaseStrategy):
    NAME = "false_breakout"
    BOOK_ID = "book_60"
    CATEGORY = "liquidity"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 10:
            return self._hold_signal("not enough candles")

        prev_high = max(c["high"] for c in candles[-10:-1])
        prev_low = min(c["low"] for c in candles[-10:-1])
        curr = candles[-1]

        if curr["low"] < prev_low and curr["close"] > prev_low:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.72,
                weight=self._get_rule_weight("long", "sweep"),
                reason=f"Swept sell-side {prev_low:.0f} then reclaimed",
                confluences=["liquidity_sweep"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if curr["high"] > prev_high and curr["close"] < prev_high:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.72,
                weight=self._get_rule_weight("short", "sweep"),
                reason=f"Swept buy-side {prev_high:.0f} then rejected",
                confluences=["liquidity_sweep"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no false breakout")
