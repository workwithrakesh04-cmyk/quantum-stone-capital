"""Flag Limits - DBD (bearish) / RBR (bullish) continuation flags."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class FlagLimitsStrategy(BaseStrategy):
    NAME = "flag_limits"
    BOOK_ID = "book_62"
    CATEGORY = "supply_demand"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 8:
            return self._hold_signal("not enough candles")

        a = candles[-6]
        c = candles[-1]

        drop1 = self._is_bearish(a) and self._candle_body(a) > 0
        tight_base = all(
            self._candle_range(x) < self._candle_range(a) * 0.7
            for x in candles[-5:-1]
        )
        drop2 = self._is_bearish(c)

        if drop1 and tight_base and drop2:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.66,
                weight=self._get_rule_weight("short", "DBD"),
                reason="DBD flag limit (bearish continuation)",
                confluences=["dbd_flag"],
                timeframe=self.timeframe,
                price=c["close"], ts=c.get("open_time", 0),
            )

        rally1 = self._is_bullish(a) and self._candle_body(a) > 0
        rally2 = self._is_bullish(c)

        if rally1 and tight_base and rally2:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.66,
                weight=self._get_rule_weight("long", "RBR"),
                reason="RBR flag limit (bullish continuation)",
                confluences=["rbr_flag"],
                timeframe=self.timeframe,
                price=c["close"], ts=c.get("open_time", 0),
            )

        return self._hold_signal("no flag limit pattern")
