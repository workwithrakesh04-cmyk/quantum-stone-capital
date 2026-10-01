"""Turtle Soup - sweep + delayed MSS confirmation."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class TurtleSoupStrategy(BaseStrategy):
    NAME = "turtle_soup"
    BOOK_ID = "fluxchart_turtle_soup"
    CATEGORY = "liquidity"
    TIMEFRAMES = ["5m", "15m", "1h"]

    HTF_BARS = 12
    MSS_OFFSET = 10
    SWEEP_LOOKBACK = 10
    MSS_CONFIRM = 3

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.HTF_BARS + self.MSS_OFFSET + self.SWEEP_LOOKBACK + 5:
            return self._hold_signal("not enough candles")

        highs = np.array([c["high"] for c in candles], dtype=np.float64)
        lows = np.array([c["low"] for c in candles], dtype=np.float64)
        closes = np.array([c["close"] for c in candles], dtype=np.float64)

        curr = candles[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]

        ref_start = -(self.HTF_BARS + self.SWEEP_LOOKBACK + 1)
        ref_end = -self.SWEEP_LOOKBACK - 1
        if abs(ref_start) > len(highs):
            return self._hold_signal("not enough lookback")

        window_high = float(np.max(highs[ref_start:ref_end]))
        window_low = float(np.min(lows[ref_start:ref_end]))

        mss_high = float(np.max(highs[-(self.MSS_OFFSET + 1):-1]))
        mss_low = float(np.min(lows[-(self.MSS_OFFSET + 1):-1]))

        for k in range(1, self.SWEEP_LOOKBACK + 1):
            i = -k
            if lows[i] < window_low and closes[i] > window_low:
                if curr_close > mss_high and closes[-1] > closes[-2]:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.72,
                        weight=self._get_rule_weight("long", "sweep"),
                        reason=f"Turtle soup LONG (sweep at bar -{k}, MSS above {mss_high:.0f})",
                        confluences=["turtle_soup", "mss_confirmation"],
                        timeframe=self.timeframe,
                        price=curr_close, ts=curr.get("open_time", 0),
                    )

            if highs[i] > window_high and closes[i] < window_high:
                if curr_close < mss_low and closes[-1] < closes[-2]:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.72,
                        weight=self._get_rule_weight("short", "sweep"),
                        reason=f"Turtle soup SHORT (sweep at bar -{k}, MSS below {mss_low:.0f})",
                        confluences=["turtle_soup", "mss_confirmation"],
                        timeframe=self.timeframe,
                        price=curr_close, ts=curr.get("open_time", 0),
                    )

        return self._hold_signal("no sweep + MSS in lookback")
