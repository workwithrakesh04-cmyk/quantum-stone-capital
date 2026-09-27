"""
Trade Router: takes an approved decision + routes it to the correct
account via the BrokerPool, respecting all rules.
"""
from dataclasses import dataclass
from typing import Optional

from brokers.broker_pool import BrokerPool
from brokers.sim_broker import Position
from core.account_router import AccountRouter, RoutingDecision


@dataclass
class RoutedTrade:
    account_name: str
    position: Optional[Position]
    allowed: bool
    reason: str


class TradeRouter:
    def __init__(self, pool: BrokerPool):
        self.pool = pool
        self.router = AccountRouter(pool)

    def place(
        self,
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        risk_amount: float = 0.0,
        preferred: str = "personal",
        is_news: bool = False,
        is_weekend: bool = False,
    ) -> RoutedTrade:
        decision = self.router.route(
            risk_amount=risk_amount,
            preferred=preferred,
            is_news=is_news,
            is_weekend=is_weekend,
        )
        if not decision.allowed:
            return RoutedTrade(
                account_name=decision.account_name,
                position=None,
                allowed=False,
                reason=decision.reason,
            )

        position = self.pool.open_trade(
            account_name=decision.account_name,
            symbol=symbol,
            side=side,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        if position is None:
            return RoutedTrade(
                account_name=decision.account_name,
                position=None,
                allowed=False,
                reason="broker_rejected_order",
            )
        return RoutedTrade(
            account_name=decision.account_name,
            position=position,
            allowed=True,
            reason=decision.reason,
        )
