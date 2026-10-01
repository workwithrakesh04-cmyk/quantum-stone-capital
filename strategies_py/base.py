"""BaseStrategy - abstract interface for all Beta Python strategies.

Self-contained: uses beta_brain.signal.Signal, not QSC's Signal.

_get_rule_weight() queries the knowledge base (option A: silent fallback).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from loguru import logger


from beta_brain.signal import Signal


# Lazily-loaded singleton, so tests without knowledge base still work
_kb = None
_kb_load_attempted = False


def _get_kb():
    global _kb, _kb_load_attempted
    if _kb_load_attempted:
        return _kb
    _kb_load_attempted = True
    try:
        from knowledge.knowledge_loader import get_knowledge_loader
        _kb = get_knowledge_loader()
    except Exception as e:
        logger.warning(f"BaseStrategy: knowledge base unavailable: {e}")
        _kb = None
    return _kb


class BaseStrategy(ABC):
    NAME: str = "base"
    BOOK_ID: str = ""
    CATEGORY: str = "general"
    TIMEFRAMES: List[str] = ["5m"]

    def __init__(self, timeframe: str = "5m"):
        self.timeframe = timeframe

    @abstractmethod
    def analyze(self, candles: List[dict]) -> Signal:
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
        """Query knowledge base for the best matching rule weight.
        Option A: silent fallback to 0.5 if knowledge base unavailable
        or BOOK_ID not found."""
        kb = _get_kb()
        if kb is None or not self.BOOK_ID:
            return 0.5
        try:
            rules = kb.get_rules(self.BOOK_ID, direction)
        except Exception:
            return 0.5
        if not rules:
            return 0.5
        if keyword:
            keyword = keyword.lower()
            matching = [r for r in rules if keyword in r.get("rule", "").lower()]
            if matching:
                return max(r.get("weight", 0.5) for r in matching)
        return max(r.get("weight", 0.5) for r in rules)
