"""LuxAlgo FVG - unfilled FVG bounce/rejection."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class LuxAlgoFVGStrategy(BaseStrategy):
    NAME = "luxalgo_fvg"
    BOOK_ID = "luxalgo_fvg"
    CATEGORY = "imbalance"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MIN_GAP_PCT = 0.05
    LOOKBACK = 15

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.LOOKBACK + 5:
            return self._hold_signal("not enough candles")

        highs = np.array([c["high"] for c in candles], dtype=np.float64)
        lows = np.array([c["low"] for c in candles], dtype=np.float64)
        closes = np.array([c["close"] for c in candles], dtype=np.float64)

        curr = candles[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]
        n = len(candles)

        best_bull_fvg = None
        best_bear_fvg = None

        for i in range(n - self.LOOKBACK, n - 2):
            if i < 1:
                continue
            c_prev = candles[i - 1]
            c_next = candles[i + 1]

            if c_next["low"] > c_prev["high"]:
                gap_pct = (c_next["low"] - c_prev["high"]) / c_prev["high"] * 100
                if gap_pct >= self.MIN_GAP_PCT:
                    fvg_low, fvg_high = c_prev["high"], c_next["low"]
                    filled = any(candles[j]["low"] <= fvg_low for j in range(i + 2, n))
                    if not filled:
                        if best_bull_fvg is None or fvg_high > best_bull_fvg[1]:
                            best_bull_fvg = (fvg_low, fvg_high, i)

            if c_next["high"] < c_prev["low"]:
                gap_pct = (c_prev["low"] - c_next["high"]) / c_next["high"] * 100
                if gap_pct >= self.MIN_GAP_PCT:
                    fvg_high, fvg_low = c_prev["low"], c_next["high"]
                    filled = any(candles[j]["high"] >= fvg_high for j in range(i + 2, n))
                    if not filled:
                        if best_bear_fvg is None or fvg_low < best_bear_fvg[0]:
                            best_bear_fvg = (fvg_low, fvg_high, i)

        if best_bull_fvg is not None:
            fvg_low, fvg_high, _ = best_bull_fvg
            if curr_low <= fvg_high and curr_close >= fvg_low and curr_close > candles[-2]["close"]:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.70,
                    weight=self._get_rule_weight("long", "FVG"),
                    reason=f"Bullish FVG bounce ({fvg_low:.0f}-{fvg_high:.0f})",
                    confluences=["fvg_bounce"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        if best_bear_fvg is not None:
            fvg_low, fvg_high, _ = best_bear_fvg
            if curr_high >= fvg_low and curr_close <= fvg_high and curr_close < candles[-2]["close"]:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.70,
                    weight=self._get_rule_weight("short", "FVG"),
                    reason=f"Bearish FVG rejection ({fvg_low:.0f}-{fvg_high:.0f})",
                    confluences=["fvg_rejection"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no FVG signal")
