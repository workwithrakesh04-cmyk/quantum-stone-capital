"""Fair Value Gap (FVG) - 3-candle imbalance fill."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class FVGStrategy(BaseStrategy):
    NAME = "fvg"
    BOOK_ID = "book_56"
    CATEGORY = "order_flow"
    TIMEFRAMES = ["1m", "5m", "15m"]
    MIN_GAP_PCT = 0.05
    MAX_AGE_BARS = 10

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 12:
            return self._hold_signal("not enough candles")

        curr = candles[-1]
        curr_price = curr["close"]

        for i in range(len(candles) - self.MAX_AGE_BARS, len(candles) - 2):
            if i < 1:
                continue
            c_prev = candles[i - 1]
            c_next = candles[i + 1]

            if c_next["low"] > c_prev["high"]:
                gap_pct = (c_next["low"] - c_prev["high"]) / c_prev["high"] * 100
                if gap_pct < self.MIN_GAP_PCT:
                    continue
                fvg_low, fvg_high = c_prev["high"], c_next["low"]
                if fvg_low <= curr["close"] <= fvg_high and self._is_bullish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.68,
                        weight=self._get_rule_weight("long", "FVG"),
                        reason=f"Bull FVG fill ({fvg_low:.0f}-{fvg_high:.0f}, {gap_pct:.2f}%)",
                        confluences=["fvg_fill"],
                        timeframe=self.timeframe,
                        price=curr_price, ts=curr.get("open_time", 0),
                    )

            if c_next["high"] < c_prev["low"]:
                gap_pct = (c_prev["low"] - c_next["high"]) / c_next["high"] * 100
                if gap_pct < self.MIN_GAP_PCT:
                    continue
                fvg_high, fvg_low = c_prev["low"], c_next["high"]
                if fvg_low <= curr["close"] <= fvg_high and self._is_bearish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.68,
                        weight=self._get_rule_weight("short", "FVG"),
                        reason=f"Bear FVG fill ({fvg_low:.0f}-{fvg_high:.0f}, {gap_pct:.2f}%)",
                        confluences=["fvg_fill"],
                        timeframe=self.timeframe,
                        price=curr_price, ts=curr.get("open_time", 0),
                    )

        return self._hold_signal("no FVG fill")
