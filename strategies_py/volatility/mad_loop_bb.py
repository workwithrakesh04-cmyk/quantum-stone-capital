"""MAD Loop BB - Mean Absolute Deviation bands breakout."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class MADBollingerStrategy(BaseStrategy):
    NAME = "mad_bb"
    BOOK_ID = "lyrors_mad_loop"
    CATEGORY = "volatility_momentum"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MA_LENGTH = 25
    MULT_UP = 1.4
    MULT_DN = 1.0

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

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.MA_LENGTH + 5:
            return self._hold_signal("not enough candles")
        closes = np.array([c["close"] for c in candles])

        ma_now = self._ema(closes, self.MA_LENGTH)
        mad_now = self._mad(closes, ma_now, self.MA_LENGTH)
        upper_now = ma_now + mad_now * self.MULT_UP
        lower_now = ma_now - mad_now * self.MULT_DN

        ma_prev = self._ema(closes[:-1], self.MA_LENGTH)
        mad_prev = self._mad(closes[:-1], ma_prev, self.MA_LENGTH)
        upper_prev = ma_prev + mad_prev * self.MULT_UP
        lower_prev = ma_prev - mad_prev * self.MULT_DN

        curr_close, prev_close = closes[-1], closes[-2]
        curr = candles[-1]

        if prev_close <= upper_prev and curr_close > upper_now:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.72,
                weight=self._get_rule_weight("long", "MAD"),
                reason=f"MAD BB crossover LONG (close > {upper_now:.2f})",
                confluences=["mad_bb_breakout"],
                timeframe=self.timeframe,
                price=curr_close, ts=curr.get("open_time", 0),
            )
        if prev_close >= lower_prev and curr_close < lower_now:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.72,
                weight=self._get_rule_weight("short", "MAD"),
                reason=f"MAD BB crossunder SHORT (close < {lower_now:.2f})",
                confluences=["mad_bb_breakdown"],
                timeframe=self.timeframe,
                price=curr_close, ts=curr.get("open_time", 0),
            )
        return self._hold_signal("no MAD BB crossover")
