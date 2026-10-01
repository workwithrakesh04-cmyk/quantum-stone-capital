"""
Shared runtime state for the dashboard.
Holds the feed aggregator, broker pool, recent decisions, routing stats.
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
    account_name: Optional[str] = None
    routing_reason: Optional[str] = None
    rule_source: Optional[str] = None
    alpha_direction: Optional[str] = None
    alpha_confidence: Optional[float] = None
    beta_direction: Optional[str] = None
    beta_confidence: Optional[float] = None
    consensus: Optional[str] = None
    size_multiplier: Optional[float] = None


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

    def routing_stats(self) -> dict:
        """Aggregate routing stats across recent decisions."""
        with self._lock:
            decisions = list(self.decisions)

        stats = {
            "personal": 0,
            "prop": 0,
            "blocked": 0,
            "by_rule_source": {"personal": 0, "prop_firm": 0, "both_blocked": 0},
            "total": len(decisions),
        }
        for d in decisions:
            if d.account_name == "personal":
                stats["personal"] += 1
            elif d.account_name == "prop":
                stats["prop"] += 1
            else:
                stats["blocked"] += 1
            if d.rule_source in stats["by_rule_source"]:
                stats["by_rule_source"][d.rule_source] += 1
        return stats

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
            "routing_stats": self.routing_stats(),
            "recent_decisions": [
                {
                    "symbol": d.symbol,
                    "direction": d.direction,
                    "confidence": d.confidence,
                    "decision": d.decision,
                    "strategy_name": d.strategy_name,
                    "reasons": d.reasons,
                    "timestamp": d.timestamp,
                    "account_name": d.account_name,
                    "routing_reason": d.routing_reason,
                    "rule_source": d.rule_source,
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
