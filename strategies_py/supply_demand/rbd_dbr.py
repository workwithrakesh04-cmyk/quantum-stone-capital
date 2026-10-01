"""RBD / DBR - Rally-Base-Drop / Drop-Base-Rally zones."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class RBDDBRStrategy(BaseStrategy):
    NAME = "rbd_dbr"
    BOOK_ID = "book_61"
    CATEGORY = "supply_demand"
    TIMEFRAMES = ["1m", "5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 6:
            return self._hold_signal("not enough candles")

        impulse, base, reaction = candles[-3], candles[-2], candles[-1]

        prior_drop = self._is_bearish(impulse) and self._candle_body(impulse) > 0
        tight_base = self._candle_range(base) < self._candle_range(impulse) * 0.6
        strong_rally = self._is_bullish(reaction) and self._candle_body(reaction) > self._candle_body(base)

        if prior_drop and tight_base and strong_rally:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.68,
                weight=self._get_rule_weight("long", "DBR"),
                reason="DBR zone pattern (drop-base-rally) - demand",
                confluences=["dbr_zone"],
                timeframe=self.timeframe,
                price=reaction["close"], ts=reaction.get("open_time", 0),
            )

        prior_rally = self._is_bullish(impulse) and self._candle_body(impulse) > 0
        strong_drop = self._is_bearish(reaction) and self._candle_body(reaction) > self._candle_body(base)

        if prior_rally and tight_base and strong_drop:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.68,
                weight=self._get_rule_weight("short", "RBD"),
                reason="RBD zone pattern (rally-base-drop) - supply",
                confluences=["rbd_zone"],
                timeframe=self.timeframe,
                price=reaction["close"], ts=reaction.get("open_time", 0),
            )

        return self._hold_signal("no RBD/DBR pattern")
