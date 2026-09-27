"""
Feed Aggregator: combines multiple live feeds into a single price source.
"""
from typing import Dict, List, Optional

from feeds.base_feed import BaseFeed, PriceUpdate


class FeedAggregator:
    def __init__(self, feeds: Optional[List[BaseFeed]] = None):
        self.feeds = feeds or []
        self._latest: Dict[str, PriceUpdate] = {}
        for f in self.feeds:
            f.add_listener(self._on_update)

    def _on_update(self, update: PriceUpdate) -> None:
        existing = self._latest.get(update.symbol)
        # Prefer sources with real bid/ask spread
        if existing is None:
            self._latest[update.symbol] = update
            return
        if update.bid > 0 and update.ask > 0 and existing.bid == existing.ask:
            self._latest[update.symbol] = update
        else:
            self._latest[update.symbol] = update

    def start_all(self) -> None:
        for f in self.feeds:
            try:
                f.start()
            except Exception as e:
                print("feed start error [" + f.name + "]: " + str(e))

    def stop_all(self) -> None:
        for f in self.feeds:
            try:
                f.stop()
            except Exception as e:
                print("feed stop error [" + f.name + "]: " + str(e))

    def latest(self, symbol: str) -> Optional[PriceUpdate]:
        return self._latest.get(symbol)

    def latest_price(self, symbol: str) -> Optional[float]:
        upd = self._latest.get(symbol)
        return upd.mid if upd else None

    def all_latest(self) -> Dict[str, PriceUpdate]:
        return dict(self._latest)

    def symbols(self) -> List[str]:
        return list(self._latest.keys())

    def health(self) -> dict:
        out = {}
        for f in self.feeds:
            out[f.name] = {"running": f.is_running(), "symbols": list(f.all_latest().keys())}
        return out
