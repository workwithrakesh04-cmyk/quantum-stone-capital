"""
BrokerPool: wires the SimBroker + live feed aggregator together
and manages both the personal and prop accounts from config/accounts.yaml.
"""
from typing import Dict, List, Optional
import yaml

from brokers.sim_broker import SimBroker, AccountState, Position


class BrokerPool:
    """
    Owns one SimBroker + subscribes it to a feed aggregator.
    Creates accounts from config/accounts.yaml.
    """

    def __init__(self, accounts_path: str = "config/accounts.yaml"):
        with open(accounts_path) as f:
            cfg = yaml.safe_load(f)

        self.broker = SimBroker()
        self.broker.connect()

        self.account_rules: Dict[str, dict] = {}
        for name, acc_cfg in cfg["accounts"].items():
            self.broker.create_account(
                name=name,
                starting_balance=acc_cfg["capital"],
                account_type=acc_cfg.get("type", "retail"),
                max_risk_per_trade=acc_cfg.get("max_risk_per_trade", 0.01),
                max_daily_loss=acc_cfg.get("max_daily_loss", 0.03),
                max_drawdown=acc_cfg.get("max_drawdown", 0.10),
                max_concurrent_positions=acc_cfg.get("max_concurrent_positions", 5),
                allow_news_trading=acc_cfg.get("allow_news_trading", True),
                allow_weekend_holding=acc_cfg.get("allow_weekend_holding", True),
                min_trading_days=acc_cfg.get("min_trading_days", 0),
                profit_target=acc_cfg.get("profit_target"),
                notes=acc_cfg.get("notes", ""),
            )
            self.account_rules[name] = acc_cfg

        # Prime broker with default prices (will be overwritten by feed)
        self.broker.set_price("BTCUSD", 40000.0)
        self.broker.set_price("ETHUSD", 2700.0)
        self.broker.set_price("XAUUSD", 2000.0)
        self.broker.set_price("EURUSD", 1.1000)
        self.broker.set_price("GBPUSD", 1.2700)
        self.broker.set_price("SPY", 770.0)

    def attach_feeds(self, aggregator) -> None:
        """Subscribe broker to a FeedAggregator so live prices update positions."""
        def on_price(update):
            self.broker.set_price(update.symbol, update.mid)

        # FeedAggregator has `feeds` list
        if hasattr(aggregator, "feeds"):
            for f in aggregator.feeds:
                f.add_listener(on_price)
        # Fallback: direct BaseFeed
        elif hasattr(aggregator, "add_listener"):
            aggregator.add_listener(on_price)

    def tick(self) -> dict:
        """Manual tick — debugging only."""
        return {}

    def snapshot(self) -> dict:
        return self.broker.snapshot()

    def get_account(self, name: str) -> Optional[AccountState]:
        return self.broker.get_account(name)

    def open_trade(self, account_name: str, symbol: str, side: str, volume: float,
                   stop_loss=None, take_profit=None) -> Optional[Position]:
        return self.broker.open_order(account_name, symbol, side, volume,
                                      stop_loss=stop_loss, take_profit=take_profit)

    def close_trade(self, account_name: str, ticket: int) -> bool:
        return self.broker.close_position(account_name, ticket)
