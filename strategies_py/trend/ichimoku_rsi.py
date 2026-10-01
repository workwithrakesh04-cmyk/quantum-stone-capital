"""Ichimoku + RSI - TK cross with cloud + RSI filter."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class IchimokuRSIStrategy(BaseStrategy):
    NAME = "ichimoku_rsi"
    BOOK_ID = "kryptonight_ichimoku"
    CATEGORY = "trend_confluence"
    TIMEFRAMES = ["5m", "15m", "1h"]
    TENKAN = 9
    KIJUN = 26
    SENKOU_B = 52
    RSI_LEN = 14

    def _donchian(self, highs, lows, period):
        if len(highs) < period:
            return (highs[-1] + lows[-1]) / 2 if len(highs) > 0 else 0.0
        return (float(np.max(highs[-period:])) + float(np.min(lows[-period:]))) / 2

    def _rsi(self, closes, period):
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        if avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    def analyze(self, candles: List[dict]) -> Signal:
        min_bars = max(self.SENKOU_B, self.KIJUN, self.TENKAN) + 30
        if len(candles) < min_bars:
            return self._hold_signal("not enough candles")

        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])

        tenkan_now = self._donchian(highs, lows, self.TENKAN)
        kijun_now = self._donchian(highs, lows, self.KIJUN)
        spanA = (tenkan_now + kijun_now) / 2
        spanB = self._donchian(highs, lows, self.SENKOU_B)
        cloud_top = max(spanA, spanB)
        cloud_bot = min(spanA, spanB)

        tenkan_prev = self._donchian(highs[:-1], lows[:-1], self.TENKAN)
        kijun_prev = self._donchian(highs[:-1], lows[:-1], self.KIJUN)

        curr_close = closes[-1]
        rsi = self._rsi(closes, self.RSI_LEN)
        curr = candles[-1]

        if tenkan_prev <= kijun_prev and tenkan_now > kijun_now:
            if curr_close > cloud_top and rsi <= 50:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.72,
                    weight=self._get_rule_weight("long", "trend"),
                    reason=f"Ichimoku LONG (RSI={rsi:.1f})",
                    confluences=["ichimoku", "tk_cross"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        if tenkan_prev >= kijun_prev and tenkan_now < kijun_now:
            if curr_close < cloud_bot and rsi >= 50:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.72,
                    weight=self._get_rule_weight("short", "trend"),
                    reason=f"Ichimoku SHORT (RSI={rsi:.1f})",
                    confluences=["ichimoku", "tk_cross"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        return self._hold_signal(f"no TK cross (RSI={rsi:.1f})")
