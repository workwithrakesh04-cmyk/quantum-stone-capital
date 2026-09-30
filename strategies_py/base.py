"""BaseStrategy - abstract interface for all Beta Python strategies.

Self-contained: uses beta_brain.signal.Signal, not QSC's Signal.
"""
from abc import ABC, abstractmethod
from typing import List


from beta_brain.signal import Signal


class BaseStrategy(ABC):
    NAME: str = "base"
    BOOK_ID: str = ""
    CATEGORY: str = "general"
    TIMEFRAMES: List[str] = ["5m"]

    def __init__(self, timeframe: str = "5m"):
        self.timeframe = timeframe

    @abstractmethod
    def analyze(self, candles: List[dict]) -> Signal:
        """candles: OHLCV dicts (oldest -> newest). Returns Signal."""
        pass

    # -------- helpers --------

    def _hold_signal(self, reason: str = "no setup") -> Signal:
        return Signal(
            strategy=self.NAME,
            direction="HOLD",
            confidence=0.0,
            book_id=self.BOOK_ID,
            timeframe=self.timeframe,
            reason=reason,
        )

    def _latest_price(self, candles: List[dict]) -> float:
        return candles[-1]["close"] if candles else 0.0

    def _latest_ts(self, candles: List[dict]) -> int:
        return candles[-1].get("open_time", 0) if candles else 0

    def _candle_body(self, c: dict) -> float:
        return abs(c["close"] - c["open"])

    def _candle_range(self, c: dict) -> float:
        return c["high"] - c["low"]

    def _is_bullish(self, c: dict) -> bool:
        return c["close"] > c["open"]

    def _is_bearish(self, c: dict) -> bool:
        return c["close"] < c["open"]

    def _is_engulfing_bullish(self, prev: dict, curr: dict) -> bool:
        return (self._is_bearish(prev) and self._is_bullish(curr)
                and curr["close"] > prev["open"]
                and curr["open"] < prev["close"])

    def _is_engulfing_bearish(self, prev: dict, curr: dict) -> bool:
        return (self._is_bullish(prev) and self._is_bearish(curr)
                and curr["close"] < prev["open"]
                and curr["open"] > prev["close"])

    def _avg_volume(self, candles: List[dict], n: int = 20) -> float:
        if len(candles) < n:
            return 0.0
        vols = [c["volume"] for c in candles[-n:]]
        return sum(vols) / n

    def _avg_range(self, candles: List[dict], n: int = 20) -> float:
        if len(candles) < n:
            return 0.0
        ranges = [self._candle_range(c) for c in candles[-n:]]
        return sum(ranges) / n

    def _get_rule_weight(self, direction: str, keyword: str = "") -> float:
        """Fallback weight. Knowledge base integration in 5a-4."""
        return 0.5
