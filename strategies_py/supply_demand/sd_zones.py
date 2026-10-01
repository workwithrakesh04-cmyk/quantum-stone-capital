"""Supply/Demand Zones - engulfing at potential zones."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class SDZonesStrategy(BaseStrategy):
    NAME = "sd_zones"
    BOOK_ID = "book_62"
    CATEGORY = "supply_demand"
    TIMEFRAMES = ["1m", "5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 5:
            return self._hold_signal("not enough candles")

        prev1, curr = candles[-2], candles[-1]

        if self._is_engulfing_bullish(prev1, curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.65,
                weight=self._get_rule_weight("long", "engulfing"),
                reason="Bullish engulfing candle - potential demand reaction",
                confluences=["engulfing"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if self._is_engulfing_bearish(prev1, curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.65,
                weight=self._get_rule_weight("short", "engulfing"),
                reason="Bearish engulfing candle - potential supply reaction",
                confluences=["engulfing"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no S/D pattern detected")
