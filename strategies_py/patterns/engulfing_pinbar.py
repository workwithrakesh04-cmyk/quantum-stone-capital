"""Engulfing + Pin Bar - candlestick reversal patterns."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class EngulfingPinBarStrategy(BaseStrategy):
    NAME = "engulfing_pinbar"
    BOOK_ID = "book_62"
    CATEGORY = "candlestick"
    TIMEFRAMES = ["1m", "5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 5:
            return self._hold_signal("not enough candles")

        prev, curr = candles[-2], candles[-1]

        if self._is_engulfing_bullish(prev, curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.66,
                weight=self._get_rule_weight("long", "engulfing"),
                reason="Bullish engulfing candle",
                confluences=["engulfing"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if self._is_engulfing_bearish(prev, curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.66,
                weight=self._get_rule_weight("short", "engulfing"),
                reason="Bearish engulfing candle",
                confluences=["engulfing"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        body = self._candle_body(curr)
        c_range = self._candle_range(curr)
        if c_range > 0 and body > 0:
            upper_wick = curr["high"] - max(curr["open"], curr["close"])
            lower_wick = min(curr["open"], curr["close"]) - curr["low"]
            wick_ratio = max(upper_wick, lower_wick) / c_range

            if wick_ratio > 0.6:
                if lower_wick > upper_wick and self._is_bullish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.64,
                        weight=self._get_rule_weight("long", "pin"),
                        reason=f"Bullish pin bar (wick={wick_ratio:.2f})",
                        confluences=["pin_bar"],
                        timeframe=self.timeframe,
                        price=curr["close"], ts=curr.get("open_time", 0),
                    )
                if upper_wick > lower_wick and self._is_bearish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.64,
                        weight=self._get_rule_weight("short", "pin"),
                        reason=f"Bearish pin bar (wick={wick_ratio:.2f})",
                        confluences=["pin_bar"],
                        timeframe=self.timeframe,
                        price=curr["close"], ts=curr.get("open_time", 0),
                    )

        return self._hold_signal("no engulfing or pin bar")
