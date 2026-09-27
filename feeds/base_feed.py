"""
Abstract live data feed.
Every concrete feed (Binance, Biquote, TickDB) implements this.
Emits PriceUpdate events to registered listeners.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional


@dataclass
class PriceUpdate:
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "unknown"

    @property
    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.last


class BaseFeed(ABC):
    name: str = "base"

    def __init__(self):
        self.listeners: List[Callable[[PriceUpdate], None]] = []
        self._latest: Dict[str, PriceUpdate] = {}
        self._running = False

    def add_listener(self, fn: Callable[[PriceUpdate], None]) -> None:
        self.listeners.append(fn)

    def _emit(self, update: PriceUpdate) -> None:
        self._latest[update.symbol] = update
        for fn in self.listeners:
            try:
                fn(update)
            except Exception as e:
                print("feed listener error [" + self.name + "] " + update.symbol + ": " + str(e))

    def latest(self, symbol: str) -> Optional[PriceUpdate]:
        return self._latest.get(symbol)

    def latest_price(self, symbol: str) -> Optional[float]:
        upd = self._latest.get(symbol)
        return upd.mid if upd else None

    def all_latest(self) -> Dict[str, PriceUpdate]:
        return dict(self._latest)

    @abstractmethod
    def start(self) -> None:
        """Start streaming (non-blocking preferred)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop streaming and clean up."""

    def is_running(self) -> bool:
        return self._running
