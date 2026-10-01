"""Absorption - high volume + narrow range = buyers/sellers absorbing aggression."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class AbsorptionStrategy(BaseStrategy):
    NAME = "absorption"
    BOOK_ID = "TD"
    CATEGORY = "order_flow"
    TIMEFRAMES = ["1m", "5m", "15m"]

    VOL_MULT = 1.4
    RANGE_MULT = 0.85

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 20:
            return self._hold_signal("not enough candles")

        curr = candles[-1]
        avg_vol = self._avg_volume(candles, 20)
        avg_range = self._avg_range(candles, 20)

        if avg_vol == 0 or avg_range == 0:
            return self._hold_signal("no volume history")

        vol_ratio = curr["volume"] / avg_vol
        range_ratio = self._candle_range(curr) / avg_range

        if not (vol_ratio > self.VOL_MULT and range_ratio < self.RANGE_MULT):
            return self._hold_signal("no absorption signature")

        c_range = curr["high"] - curr["low"]
        if c_range <= 0:
            return self._hold_signal("zero range")

        close_pos = (curr["close"] - curr["low"]) / c_range

        if close_pos > 0.6:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.68,
                weight=self._get_rule_weight("long", "absorption"),
                reason=f"Absorption LONG (vol={vol_ratio:.2f}x range={range_ratio:.2f}x)",
                confluences=["absorption", "high_volume"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if close_pos < 0.4:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.68,
                weight=self._get_rule_weight("short", "absorption"),
                reason=f"Absorption SHORT (vol={vol_ratio:.2f}x range={range_ratio:.2f}x)",
                confluences=["absorption", "high_volume"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("absorption but no direction")
