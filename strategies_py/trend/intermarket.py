"""Intermarket - simple 3-window trend continuation."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class IntermarketStrategy(BaseStrategy):
    NAME = "intermarket"
    BOOK_ID = "VP"
    CATEGORY = "intermarket"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MIN_TREND_PCT = 0.5

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 30:
            return self._hold_signal("not enough candles")
        closes = [c["close"] for c in candles[-30:]]
        first_avg = sum(closes[:10]) / 10
        mid_avg = sum(closes[10:20]) / 10
        last_avg = sum(closes[20:]) / 10

        curr = candles[-1]

        if first_avg < mid_avg < last_avg:
            move_pct = (last_avg - first_avg) / first_avg * 100
            if move_pct >= self.MIN_TREND_PCT and self._is_bullish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.62,
                    weight=self._get_rule_weight("long", "trend"),
                    reason=f"Bullish trend {move_pct:.2f}%",
                    confluences=["trend_continuation"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        if first_avg > mid_avg > last_avg:
            move_pct = (first_avg - last_avg) / first_avg * 100
            if move_pct >= self.MIN_TREND_PCT and self._is_bearish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.62,
                    weight=self._get_rule_weight("short", "trend"),
                    reason=f"Bearish trend {move_pct:.2f}%",
                    confluences=["trend_continuation"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no clear trend")
