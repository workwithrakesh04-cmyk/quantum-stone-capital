"""Trapped Traders - sweep of prior swing high/low then reclaim."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class TrappedTradersStrategy(BaseStrategy):
    NAME = "trapped_traders"
    BOOK_ID = "TOF"
    CATEGORY = "order_flow"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 10:
            return self._hold_signal("not enough candles")

        curr = candles[-1]
        lookback = candles[-8:-1]
        if not lookback:
            return self._hold_signal("no lookback")

        prior_high = max(c["high"] for c in lookback)
        prior_low = min(c["low"] for c in lookback)

        # Trapped sellers: new low, closed back above, bullish body
        if curr["low"] < prior_low and curr["close"] > prior_low and self._is_bullish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.70,
                weight=self._get_rule_weight("long", "trapped"),
                reason=f"Trapped sellers - swept {prior_low:.0f}",
                confluences=["trapped_traders"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        # Trapped buyers: new high, closed back below, bearish body
        if curr["high"] > prior_high and curr["close"] < prior_high and self._is_bearish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.70,
                weight=self._get_rule_weight("short", "trapped"),
                reason=f"Trapped buyers - swept {prior_high:.0f}",
                confluences=["trapped_traders"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no trapped traders")
