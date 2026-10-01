"""Diamond + CanCan pattern - contraction + drive failure."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class DiamondCanCanStrategy(BaseStrategy):
    NAME = "diamond_cancan"
    BOOK_ID = "book_62"
    CATEGORY = "pattern"
    TIMEFRAMES = ["5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 8:
            return self._hold_signal("not enough candles")

        ranges = [self._candle_range(c) for c in candles[-8:]]
        early = sum(ranges[:4]) / 4
        late = sum(ranges[4:]) / 4

        if early == 0:
            return self._hold_signal("zero early range")

        diamond = late / early < 0.6
        curr = candles[-1]
        highs = [c["high"] for c in candles[-6:]]
        lows = [c["low"] for c in candles[-6:]]

        rising_highs = highs[-1] > highs[-3] > highs[-5] if len(highs) >= 5 else False
        rising_lows = lows[-1] > lows[-3] > lows[-5] if len(lows) >= 5 else False

        if diamond and rising_highs and self._is_bearish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.68,
                weight=self._get_rule_weight("short", "diamond"),
                reason=f"Diamond contraction + rising highs (ratio={late/early:.2f})",
                confluences=["diamond", "cancan"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if diamond and rising_lows and self._is_bullish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.68,
                weight=self._get_rule_weight("long", "diamond"),
                reason=f"Diamond contraction + falling lows (ratio={late/early:.2f})",
                confluences=["diamond", "cancan"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no diamond/cancan")
