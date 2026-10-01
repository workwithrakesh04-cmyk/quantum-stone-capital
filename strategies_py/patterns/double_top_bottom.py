"""Double Top / Double Bottom - classical pattern."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class DoubleTopBottomStrategy(BaseStrategy):
    NAME = "double_top_bottom"
    BOOK_ID = "book_62"
    CATEGORY = "pattern"
    TIMEFRAMES = ["15m", "1h"]
    TOLERANCE = 0.02

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 20:
            return self._hold_signal("not enough candles")

        recent = candles[-20:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]

        p1_high = max(highs[:7])
        p2_high = max(highs[13:])
        valley = min(lows[7:13])

        if abs(p1_high - p2_high) / p1_high < self.TOLERANCE:
            curr = candles[-1]
            if curr["close"] < valley:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.68,
                    weight=self._get_rule_weight("short", "double top"),
                    reason=f"Double top broke {valley:.0f}",
                    confluences=["double_top"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        p1_low = min(lows[:7])
        p2_low = min(lows[13:])
        peak = max(highs[7:13])

        if abs(p1_low - p2_low) / p1_low < self.TOLERANCE:
            curr = candles[-1]
            if curr["close"] > peak:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.68,
                    weight=self._get_rule_weight("long", "double bottom"),
                    reason=f"Double bottom broke {peak:.0f}",
                    confluences=["double_bottom"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no double top/bottom")
