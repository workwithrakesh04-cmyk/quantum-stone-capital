"""Break of Structure (BOS) / Change of Character (CHoCH).

BOS   = price breaks a prior swing in the SAME direction as trend -> continuation
CHoCH = price breaks the last OPPOSITE swing -> potential reversal

Uses ATR as a confirmation buffer to avoid noise breaks.
"""
from typing import List, Optional
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class BOSCHoCHStrategy(BaseStrategy):
    NAME = "bos_choch"
    BOOK_ID = "ftm_smc"
    CATEGORY = "ict_smc"
    TIMEFRAMES = ["1m", "5m", "15m"]

    SWING_LOOKBACK = 3
    ATR_LEN = 14
    BREAK_BUFFER_ATR = 0.10
    MIN_SWINGS = 3

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h, l, pc = highs[-i], lows[-i], closes[-i - 1]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return float(np.mean(trs))

    def _find_swings(self, candles, lookback):
        swings = []
        n = len(candles)
        if n < 2 * lookback + 1:
            return swings
        for i in range(lookback, n - lookback):
            is_high = all(candles[i]["high"] >= candles[i - j]["high"] for j in range(1, lookback + 1)) and \
                      all(candles[i]["high"] >= candles[i + j]["high"] for j in range(1, lookback + 1))
            is_low = all(candles[i]["low"] <= candles[i - j]["low"] for j in range(1, lookback + 1)) and \
                     all(candles[i]["low"] <= candles[i + j]["low"] for j in range(1, lookback + 1))
            if is_high:
                swings.append({"type": "H", "idx": i, "price": float(candles[i]["high"])})
            elif is_low:
                swings.append({"type": "L", "idx": i, "price": float(candles[i]["low"])})
        return swings

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 40:
            return self._hold_signal("not enough candles")

        highs = np.array([c["high"] for c in candles], dtype=np.float64)
        lows = np.array([c["low"] for c in candles], dtype=np.float64)
        closes = np.array([c["close"] for c in candles], dtype=np.float64)

        atr = self._atr(highs, lows, closes, self.ATR_LEN)
        if atr <= 0:
            return self._hold_signal("ATR is zero")

        # Find swings on candles up to (but not including) the last bar
        swings = self._find_swings(candles[:-1], self.SWING_LOOKBACK)
        if len(swings) < self.MIN_SWINGS:
            return self._hold_signal("not enough swings")

        last_close = float(closes[-1])
        buffer = atr * self.BREAK_BUFFER_ATR

        # Recent swings (last 6, chronological)
        recent = swings[-6:]

        # Prior swing high and low (most recent)
        swing_highs = [s for s in recent if s["type"] == "H"]
        swing_lows = [s for s in recent if s["type"] == "L"]

        if not swing_highs or not swing_lows:
            return self._hold_signal("missing swing side")

        last_high = swing_highs[-1]["price"]
        last_low = swing_lows[-1]["price"]
        prev_high = swing_highs[-2]["price"] if len(swing_highs) >= 2 else None
        prev_low = swing_lows[-2]["price"] if len(swing_lows) >= 2 else None

        # Order of the last two swings determines BOS vs CHoCH
        last_two = recent[-2:]
        last_two_types = [s["type"] for s in last_two]

        curr = candles[-1]

        # BULLISH break: close > last_high + buffer
        if last_close > last_high + buffer:
            # BOS: the prior swing structure was already bullish (higher highs, higher lows)
            if prev_high is not None and prev_low is not None:
                structure_bullish = last_high > prev_high and last_low > prev_low
            else:
                structure_bullish = False

            if structure_bullish:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.72,
                    weight=self._get_rule_weight("long", "break"),
                    reason=f"Bullish BOS above {last_high:.2f}",
                    confluences=["bos", "bullish_structure"],
                    timeframe=self.timeframe,
                    price=last_close, ts=curr.get("open_time", 0),
                )
            else:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.68,
                    weight=self._get_rule_weight("long", "choch"),
                    reason=f"Bullish CHoCH above {last_high:.2f}",
                    confluences=["choch", "reversal"],
                    timeframe=self.timeframe,
                    price=last_close, ts=curr.get("open_time", 0),
                )

        # BEARISH break: close < last_low - buffer
        if last_close < last_low - buffer:
            if prev_high is not None and prev_low is not None:
                structure_bearish = last_high < prev_high and last_low < prev_low
            else:
                structure_bearish = False

            if structure_bearish:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.72,
                    weight=self._get_rule_weight("short", "break"),
                    reason=f"Bearish BOS below {last_low:.2f}",
                    confluences=["bos", "bearish_structure"],
                    timeframe=self.timeframe,
                    price=last_close, ts=curr.get("open_time", 0),
                )
            else:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.68,
                    weight=self._get_rule_weight("short", "choch"),
                    reason=f"Bearish CHoCH below {last_low:.2f}",
                    confluences=["choch", "reversal"],
                    timeframe=self.timeframe,
                    price=last_close, ts=curr.get("open_time", 0),
                )

        return self._hold_signal("no break")
