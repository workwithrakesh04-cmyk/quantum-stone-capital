"""
Shared runtime state for the dashboard.
Holds the feed aggregator, broker pool, and recent brain decisions.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import List, Optional

from feeds.default_feed import build_default_aggregator
from feeds.aggregator import FeedAggregator
from brokers.broker_pool import BrokerPool


@dataclass
class Decision:
    symbol: str
    direction: str
    confidence: float
    decision: str
    strategy_name: Optional[str]
    reasons: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AppState:
    def __init__(self, accounts_path: str = "config/accounts.yaml"):
        self.feeds: FeedAggregator = build_default_aggregator()
        self.pool: BrokerPool = BrokerPool(accounts_path=accounts_path)
        # Wire the feeds into the broker so live prices update account equity
        self.pool.attach_feeds(self.feeds)
        self.decisions: List[Decision] = []
        self._lock = Lock()
        self.started_at = datetime.now(timezone.utc).isoformat()

    def start(self) -> None:
        self.feeds.start_all()

    def stop(self) -> None:
        try:
            self.feeds.stop_all()
        except Exception:
            pass

    def add_decision(self, d: Decision) -> None:
        with self._lock:
            self.decisions.append(d)
            if len(self.decisions) > 200:
                self.decisions = self.decisions[-200:]

    def recent_decisions(self, n: int = 20) -> List[Decision]:
        with self._lock:
            return list(self.decisions[-n:])

    def snapshot(self) -> dict:
        feed_prices = {}
        for sym, upd in self.feeds.all_latest().items():
            feed_prices[sym] = {
                "bid": upd.bid,
                "ask": upd.ask,
                "mid": upd.mid,
                "source": upd.source,
                "timestamp": upd.timestamp,
            }
        broker_snapshot = self.pool.snapshot()
        return {
            "started_at": self.started_at,
            "now": datetime.now(timezone.utc).isoformat(),
            "prices": feed_prices,
            "accounts": broker_snapshot.get("accounts", {}),
            "broker_prices": broker_snapshot.get("prices", {}),
            "recent_decisions": [
                {
                    "symbol": d.symbol,
                    "direction": d.direction,
                    "confidence": d.confidence,
                    "decision": d.decision,
                    "strategy_name": d.strategy_name,
                    "reasons": d.reasons,
                    "timestamp": d.timestamp,
                }
                for d in self.recent_decisions(20)
            ],
        }


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state


def reset_state() -> None:
    global _state
    if _state is not None:
        try:
            _state.stop()
        except Exception:
            pass
    _state = None
