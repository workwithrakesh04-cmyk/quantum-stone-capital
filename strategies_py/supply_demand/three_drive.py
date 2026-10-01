"""3Drive Pattern - exhaustion after three progressively weaker drives."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class ThreeDriveStrategy(BaseStrategy):
    NAME = "three_drive"
    BOOK_ID = "book_62"
    CATEGORY = "pattern"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 12:
            return self._hold_signal("not enough candles")

        g1 = candles[-12:-9]
        g2 = candles[-9:-6]
        g3 = candles[-6:-3]

        h1 = max(c["high"] for c in g1)
        h2 = max(c["high"] for c in g2)
        h3 = max(c["high"] for c in g3)
        r1 = max(c["high"] for c in g1) - min(c["low"] for c in g1)
        r2 = max(c["high"] for c in g2) - min(c["low"] for c in g2)
        r3 = max(c["high"] for c in g3) - min(c["low"] for c in g3)

        l1 = min(c["low"] for c in g1)
        l2 = min(c["low"] for c in g2)
        l3 = min(c["low"] for c in g3)

        curr = candles[-1]

        if h1 < h2 < h3 and r1 >= r2 * 0.9 and r2 >= r3 * 0.9:
            if self._is_bearish(curr) and self._candle_body(curr) > r3 * 0.4:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.70,
                    weight=self._get_rule_weight("short", "3drive"),
                    reason="3Drive top exhausted",
                    confluences=["3drive"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        if l1 > l2 > l3 and r1 >= r2 * 0.9 and r2 >= r3 * 0.9:
            if self._is_bullish(curr) and self._candle_body(curr) > r3 * 0.4:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.70,
                    weight=self._get_rule_weight("long", "3drive"),
                    reason="3Drive bottom exhausted",
                    confluences=["3drive"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no 3Drive exhaustion")
