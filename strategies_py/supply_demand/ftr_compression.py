"""Failure to Return + Compression - narrow range then breakout."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class FTRCompressionStrategy(BaseStrategy):
    NAME = "ftr_compression"
    BOOK_ID = "book_62"
    CATEGORY = "supply_demand"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 15:
            return self._hold_signal("not enough candles")

        recent_ranges = [self._candle_range(c) for c in candles[-5:]]
        prior_ranges = [self._candle_range(c) for c in candles[-15:-5]]

        avg_recent = sum(recent_ranges) / len(recent_ranges) if recent_ranges else 0
        avg_prior = sum(prior_ranges) / len(prior_ranges) if prior_ranges else 0

        if avg_prior == 0:
            return self._hold_signal("no prior range")

        compression_ratio = avg_recent / avg_prior
        if compression_ratio >= 0.6:
            return self._hold_signal(f"no compression (ratio={compression_ratio:.2f})")

        curr = candles[-1]

        if self._is_bullish(curr) and self._candle_body(curr) > avg_recent:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.70,
                weight=self._get_rule_weight("long", "compression"),
                reason=f"Bullish compression breakout (ratio={compression_ratio:.2f})",
                confluences=["compression", "breakout"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if self._is_bearish(curr) and self._candle_body(curr) > avg_recent:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.70,
                weight=self._get_rule_weight("short", "compression"),
                reason=f"Bearish compression breakout (ratio={compression_ratio:.2f})",
                confluences=["compression", "breakout"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("compressed but no breakout")
