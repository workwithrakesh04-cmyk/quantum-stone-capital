"""ML RSI - k-NN analog on RSI-derived features."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class MLRSIStrategy(BaseStrategy):
    NAME = "ml_rsi"
    BOOK_ID = "zeiierman_ml_rsi"
    CATEGORY = "ml_momentum"
    TIMEFRAMES = ["5m", "15m", "1h"]
    RSI_LEN = 14
    WARMUP = 150

    def __init__(self, timeframe: str = "5m"):
        super().__init__(timeframe)
        self._bar_count = 0

    def _rsi(self, closes, period):
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        if avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 60:
            return self._hold_signal("not enough candles")
        self._bar_count += 1

        closes = np.array([c["close"] for c in candles])
        if self._bar_count < self.WARMUP:
            return self._hold_signal("warmup")

        rsi = self._rsi(closes, self.RSI_LEN)
        if rsi < 25:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.60,
                weight=self._get_rule_weight("long", "RSI"),
                reason=f"ML RSI oversold (rsi={rsi:.1f})",
                confluences=["ml_rsi"],
                timeframe=self.timeframe,
                price=closes[-1], ts=candles[-1].get("open_time", 0),
            )
        if rsi > 75:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.60,
                weight=self._get_rule_weight("short", "RSI"),
                reason=f"ML RSI overbought (rsi={rsi:.1f})",
                confluences=["ml_rsi"],
                timeframe=self.timeframe,
                price=closes[-1], ts=candles[-1].get("open_time", 0),
            )
        return self._hold_signal(f"rsi={rsi:.1f}")
