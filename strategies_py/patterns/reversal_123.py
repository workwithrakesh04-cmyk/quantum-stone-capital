"""1-2-3 Reversal - pivot-based pattern with neckline break."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class Reversal123Strategy(BaseStrategy):
    NAME = "reversal_123"
    BOOK_ID = "agpro_123"
    CATEGORY = "pattern"
    TIMEFRAMES = ["5m", "15m", "1h"]
    LEFT_BARS = 2
    RIGHT_BARS = 2
    ATR_LEN = 14
    MIN_LEG_ATR = 0.65
    MIN_POINT3_HOLD_ATR = 0.05
    MIN_RETRACE = 0.15
    MAX_RETRACE = 0.92
    BREAK_BUFFER_ATR = 0.05

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h = highs[-i]; l = lows[-i]; pc = closes[-i - 1]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return float(np.mean(trs))

    def _find_pivots(self, values, left, right):
        pivots = []
        n = len(values)
        for i in range(left, n - right):
            is_high = all(values[i] > values[i - j] for j in range(1, left + 1)) and \
                      all(values[i] > values[i + j] for j in range(1, right + 1))
            is_low = all(values[i] < values[i - j] for j in range(1, left + 1)) and \
                     all(values[i] < values[i + j] for j in range(1, right + 1))
            if is_high:
                pivots.append((i, values[i], 1))
            elif is_low:
                pivots.append((i, values[i], -1))
        return pivots

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 30:
            return self._hold_signal("not enough candles")

        highs = np.array([c["high"] for c in candles], dtype=np.float64)
        lows = np.array([c["low"] for c in candles], dtype=np.float64)
        closes = np.array([c["close"] for c in candles], dtype=np.float64)

        atr = self._atr(highs, lows, closes, self.ATR_LEN)
        if atr <= 0:
            return self._hold_signal("ATR is zero")

        pivots_h = self._find_pivots(highs, self.LEFT_BARS, self.RIGHT_BARS)
        pivots_l = self._find_pivots(lows, self.LEFT_BARS, self.RIGHT_BARS)
        all_pivots = sorted(pivots_h + pivots_l, key=lambda p: p[0])
        if len(all_pivots) < 3:
            return self._hold_signal("not enough pivots")

        p1_idx, p1_price, p1_type = all_pivots[-3]
        p2_idx, p2_price, p2_type = all_pivots[-2]
        p3_idx, p3_price, p3_type = all_pivots[-1]

        is_bull_chain = (p1_type == -1 and p2_type == 1 and p3_type == -1)
        is_bear_chain = (p1_type == 1 and p2_type == -1 and p3_type == 1)
        curr = candles[-1]
        curr_close = closes[-1]

        if is_bull_chain:
            leg = abs(p2_price - p1_price)
            hold = p3_price - p1_price
            retrace = (p2_price - p3_price) / leg if leg > 0 else 0
            if (leg >= atr * self.MIN_LEG_ATR and
                hold >= atr * self.MIN_POINT3_HOLD_ATR and
                self.MIN_RETRACE <= retrace <= self.MAX_RETRACE):
                neckline = p2_price
                if curr_close > neckline + atr * self.BREAK_BUFFER_ATR:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.72,
                        weight=self._get_rule_weight("long", "1-2-3"),
                        reason=f"Bullish 1-2-3 break above {neckline:.0f}",
                        confluences=["pattern_123", "neckline_break"],
                        timeframe=self.timeframe,
                        price=curr_close, ts=curr.get("open_time", 0),
                    )

        if is_bear_chain:
            leg = abs(p2_price - p1_price)
            hold = p1_price - p3_price
            retrace = (p3_price - p2_price) / leg if leg > 0 else 0
            if (leg >= atr * self.MIN_LEG_ATR and
                hold >= atr * self.MIN_POINT3_HOLD_ATR and
                self.MIN_RETRACE <= retrace <= self.MAX_RETRACE):
                neckline = p2_price
                if curr_close < neckline - atr * self.BREAK_BUFFER_ATR:
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.72,
                        weight=self._get_rule_weight("short", "1-2-3"),
                        reason=f"Bearish 1-2-3 break below {neckline:.0f}",
                        confluences=["pattern_123", "neckline_break"],
                        timeframe=self.timeframe,
                        price=curr_close, ts=curr.get("open_time", 0),
                    )

        return self._hold_signal("no valid 1-2-3 pattern")
