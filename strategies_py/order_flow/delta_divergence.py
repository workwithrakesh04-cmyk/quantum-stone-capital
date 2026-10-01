"""Delta Divergence - price vs delta disagreement (bullish/bearish)."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class DeltaDivergenceStrategy(BaseStrategy):
    NAME = "delta_divergence"
    BOOK_ID = "TD"
    CATEGORY = "order_flow"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 10:
            return self._hold_signal("not enough candles")

        curr = candles[-1]
        prev = candles[-2]

        curr_delta = curr.get("buy_volume", 0) - curr.get("sell_volume", 0)
        prev_delta = prev.get("buy_volume", 0) - prev.get("sell_volume", 0)

        curr_move = curr["close"] - curr["open"]
        prev_move = prev["close"] - prev["open"]

        # Bullish: price down, delta up
        if curr_move < 0 and curr_delta > 0 and prev_delta < 0:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.72,
                weight=self._get_rule_weight("long", "divergence"),
                reason="Bullish delta divergence (price down, delta up)",
                confluences=["delta_positive", "divergence"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        # Bearish: price up, delta down
        if curr_move > 0 and curr_delta < 0 and prev_delta > 0:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.72,
                weight=self._get_rule_weight("short", "divergence"),
                reason="Bearish delta divergence (price up, delta down)",
                confluences=["delta_negative", "divergence"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no delta divergence")
