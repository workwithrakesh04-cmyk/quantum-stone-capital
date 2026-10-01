"""Head and Shoulders - classical reversal with neckline break."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class HeadShouldersStrategy(BaseStrategy):
    NAME = "head_shoulders"
    BOOK_ID = "book_62"
    CATEGORY = "pattern"
    TIMEFRAMES = ["15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 15:
            return self._hold_signal("not enough candles")

        recent = candles[-15:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]

        ls_high = max(highs[:5])
        head_high = max(highs[5:10])
        rs_high = max(highs[10:])

        if head_high > ls_high and head_high > rs_high:
            if abs(ls_high - rs_high) / ls_high < 0.02:
                neckline = min(lows[5:10])
                curr = candles[-1]
                if curr["close"] < neckline:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.72,
                        weight=self._get_rule_weight("short", "head"),
                        reason=f"H&S broke neckline {neckline:.0f}",
                        confluences=["head_shoulders"],
                        timeframe=self.timeframe,
                        price=curr["close"], ts=curr.get("open_time", 0),
                    )

        ls_low = min(lows[:5])
        head_low = min(lows[5:10])
        rs_low = min(lows[10:])

        if head_low < ls_low and head_low < rs_low:
            if abs(ls_low - rs_low) / ls_low < 0.02:
                neckline = max(highs[5:10])
                curr = candles[-1]
                if curr["close"] > neckline:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.72,
                        weight=self._get_rule_weight("long", "head"),
                        reason=f"Inverse H&S broke neckline {neckline:.0f}",
                        confluences=["inverse_head_shoulders"],
                        timeframe=self.timeframe,
                        price=curr["close"], ts=curr.get("open_time", 0),
                    )

        return self._hold_signal("no H&S pattern")
