"""
Abstract broker interface.
Every concrete broker (paper, MT5, Binance, OANDA) implements this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BrokerOrder:
    ticket: int
    symbol: str
    side: str            # "buy" | "sell"
    volume: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = "open"   # "open" | "closed"


@dataclass
class BrokerAccount:
    balance: float
    equity: float
    margin: float
    free_margin: float
    currency: str = "USD"


class BaseBroker(ABC):
    name: str = "base"

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Return True on success."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and clean up."""

    @abstractmethod
    def account_info(self) -> BrokerAccount:
        """Return current account state."""

    @abstractmethod
    def last_price(self, symbol: str) -> Optional[float]:
        """Return the latest bid/mid price."""

    @abstractmethod
    def open_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        order_type: str = "market",
    ) -> Optional[BrokerOrder]:
        """Place a new order."""

    @abstractmethod
    def close_order(self, ticket: int) -> bool:
        """Close an open order by ticket."""

    @abstractmethod
    def open_orders(self) -> List[BrokerOrder]:
        """List all open orders."""

    def __repr__(self) -> str:
        return "<Broker " + self.name + ">"
