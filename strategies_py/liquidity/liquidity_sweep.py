"""Liquidity Sweep - equal highs/lows swept then reclaimed."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class LiquiditySweepStrategy(BaseStrategy):
    NAME = "liquidity_sweep"
    BOOK_ID = "book_60"
    CATEGORY = "liquidity"
    TIMEFRAMES = ["1m", "5m", "15m"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 8:
            return self._hold_signal("not enough candles")

        prev = candles[-8:-1]
        if not prev:
            return self._hold_signal("no context")

        highs = [c["high"] for c in prev]
        lows = [c["low"] for c in prev]
        max_h = max(highs)
        min_l = min(lows)

        equal_highs = sum(1 for h in highs if abs(h - max_h) / max_h < 0.0005)
        equal_lows = sum(1 for l in lows if abs(l - min_l) / min_l < 0.0005)

        curr = candles[-1]

        if equal_lows >= 2:
            if curr["low"] < min_l and curr["close"] > min_l and self._is_bullish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.74,
                    weight=self._get_rule_weight("long", "sweep"),
                    reason=f"Sweep below equal lows {min_l:.0f} then reclaimed",
                    confluences=["liquidity_sweep", "equal_lows"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        if equal_highs >= 2:
            if curr["high"] > max_h and curr["close"] < max_h and self._is_bearish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.74,
                    weight=self._get_rule_weight("short", "sweep"),
                    reason=f"Sweep above equal highs {max_h:.0f} then rejected",
                    confluences=["liquidity_sweep", "equal_highs"],
                    timeframe=self.timeframe,
                    price=curr["close"], ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no liquidity sweep")
