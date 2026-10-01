"""MAD Loop Combined - BB + FL agreement."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class MADCombinedStrategy(BaseStrategy):
    NAME = "mad_combined"
    BOOK_ID = "lyrors_mad_loop"
    CATEGORY = "confluence"
    TIMEFRAMES = ["5m", "15m", "1h"]
    BB_MA_LENGTH = 25
    BB_MULT_UP = 1.4
    BB_MULT_DN = 1.0
    FL_LOOP_A = 10
    FL_LOOP_B = 60
    FL_THRESHOLD_LONG = 23
    FL_THRESHOLD_SHORT = 3

    def _ema(self, values, period):
        if len(values) < period:
            return float(np.mean(values)) if len(values) > 0 else 0.0
        k = 2.0 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return float(ema)

    def _mad(self, values, ma, period):
        if len(values) < period:
            return 0.0
        return float(np.mean(np.abs(values[-period:] - ma)))

    def _bb_score(self, closes):
        if len(closes) < self.BB_MA_LENGTH + 5:
            return 0
        ma = self._ema(closes, self.BB_MA_LENGTH)
        mad = self._mad(closes, ma, self.BB_MA_LENGTH)
        upper, lower = ma + mad * self.BB_MULT_UP, ma - mad * self.BB_MULT_DN
        ma_prev = self._ema(closes[:-1], self.BB_MA_LENGTH)
        mad_prev = self._mad(closes[:-1], ma_prev, self.BB_MA_LENGTH)
        upper_prev = ma_prev + mad_prev * self.BB_MULT_UP
        lower_prev = ma_prev - mad_prev * self.BB_MULT_DN
        c, p = closes[-1], closes[-2]
        if p <= upper_prev and c > upper: return 1
        if p >= lower_prev and c < lower: return -1
        return 0

    def _fl_score(self, closes):
        if len(closes) < self.FL_LOOP_B + 5:
            return 0
        def loop_score(arr):
            if len(arr) < self.FL_LOOP_B + 1: return 0
            c = arr[-1]
            s = 0
            for i in range(self.FL_LOOP_A, self.FL_LOOP_B + 1):
                s += 1 if c > arr[-1 - i] else -1
            return s
        now = loop_score(closes)
        prev = loop_score(closes[:-1])
        if prev <= self.FL_THRESHOLD_LONG and now > self.FL_THRESHOLD_LONG: return 1
        if prev >= self.FL_THRESHOLD_SHORT and now < self.FL_THRESHOLD_SHORT: return -1
        return 0

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.FL_LOOP_B + 10:
            return self._hold_signal("not enough candles")
        closes = np.array([c["close"] for c in candles])
        bb_now = self._bb_score(closes)
        fl_now = self._fl_score(closes)
        curr = candles[-1]

        if bb_now == 1 and fl_now == 1:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.72,
                weight=self._get_rule_weight("long", "combined"),
                reason="MAD Combined LONG (bb=fl=1)",
                confluences=["mad_combined"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        if bb_now == -1 and fl_now == -1:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.72,
                weight=self._get_rule_weight("short", "combined"),
                reason="MAD Combined SHORT (bb=fl=-1)",
                confluences=["mad_combined"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        return self._hold_signal(f"bb={bb_now} fl={fl_now}")
