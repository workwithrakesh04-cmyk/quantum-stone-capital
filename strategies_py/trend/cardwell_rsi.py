"""Cardwell Range RSI - bull/bear range regime."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class CardwellRSIStrategy(BaseStrategy):
    NAME = "cardwell_rsi"
    BOOK_ID = "markittick_cardwell"
    CATEGORY = "regime_rsi"
    TIMEFRAMES = ["5m", "15m", "1h"]
    RSI_LEN = 14
    TREND_LEN = 50
    BULL_LO, BULL_HI = 40, 80
    BEAR_LO, BEAR_HI = 20, 60

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

    def _regime_at(self, closes):
        if len(closes) < self.TREND_LEN + 2:
            return 0
        rsi = self._rsi(closes, self.RSI_LEN)
        sma = float(np.mean(closes[-self.TREND_LEN:]))
        if closes[-1] > sma and self.BULL_LO <= rsi <= self.BULL_HI:
            return 1
        if closes[-1] < sma and self.BEAR_LO <= rsi <= self.BEAR_HI:
            return -1
        return 0

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.TREND_LEN + 10:
            return self._hold_signal("not enough candles")
        closes = np.array([c["close"] for c in candles])

        regime_now = self._regime_at(closes)
        regime_prev = self._regime_at(closes[:-1])

        if regime_now == 0 or regime_now == regime_prev:
            return self._hold_signal(f"regime={regime_now}")

        curr = candles[-1]
        rsi = self._rsi(closes, self.RSI_LEN)

        if regime_now == 1:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.74,
                weight=self._get_rule_weight("long", "regime"),
                reason=f"Cardwell BULL regime (RSI={rsi:.1f})",
                confluences=["cardwell_bull"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        return Signal(
            strategy=self.NAME, book_id=self.BOOK_ID,
            direction="SHORT", confidence=0.74,
            weight=self._get_rule_weight("short", "regime"),
            reason=f"Cardwell BEAR regime (RSI={rsi:.1f})",
            confluences=["cardwell_bear"],
            timeframe=self.timeframe,
            price=closes[-1], ts=curr.get("open_time", 0),
        )
