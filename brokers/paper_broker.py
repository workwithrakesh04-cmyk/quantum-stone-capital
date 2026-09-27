"""
Paper-trading broker: simulated in-memory execution.
No real broker connection. Useful for backtests and dry runs.
"""
from typing import Dict, List, Optional

from brokers.base_broker import BaseBroker, BrokerOrder, BrokerAccount


class PaperBroker(BaseBroker):
    name = "paper"

    def __init__(
        self,
        starting_balance: float = 10000.0,
        commission_per_unit: float = 0.0,
        slippage_pct: float = 0.0002,
        prices: Optional[Dict[str, float]] = None,
    ):
        self._balance = starting_balance
        self._equity = starting_balance
        self._margin = 0.0
        self._commission = commission_per_unit
        self._slippage_pct = slippage_pct
        self._prices: Dict[str, float] = dict(prices or {})
        self._orders: Dict[int, BrokerOrder] = {}
        self._next_ticket = 1
        self._connected = False

    # --- lifecycle ---
    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    # --- account ---
    def account_info(self) -> BrokerAccount:
        used_margin = 0.0
        for o in self._orders.values():
            if o.status == "open":
                used_margin += abs(o.volume * o.entry_price) * 0.01  # 1% margin
        self._margin = used_margin
        return BrokerAccount(
            balance=self._balance,
            equity=self._equity,
            margin=used_margin,
            free_margin=self._balance - used_margin,
        )

    # --- prices ---
    def set_price(self, symbol: str, price: float) -> None:
        """Update the simulated price and mark open orders to market."""
        self._prices[symbol] = price
        self._recompute_equity()

    def last_price(self, symbol: str) -> Optional[float]:
        return self._prices.get(symbol)

    def _recompute_equity(self) -> None:
        unrealized = 0.0
        for o in self._orders.values():
            if o.status != "open":
                continue
            price = self._prices.get(o.symbol, o.entry_price)
            if o.side == "buy":
                unrealized += (price - o.entry_price) * o.volume
            else:
                unrealized += (o.entry_price - price) * o.volume
        self._equity = self._balance + unrealized

    # --- orders ---
    def open_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        order_type: str = "market",
    ) -> Optional[BrokerOrder]:
        if not self._connected:
            return None
        if side not in ("buy", "sell"):
            return None
        if volume <= 0:
            return None
        price = self._prices.get(symbol)
        if price is None:
            return None

        # Apply slippage
        if side == "buy":
            fill = price * (1 + self._slippage_pct)
        else:
            fill = price * (1 - self._slippage_pct)

        # Commission
        self._balance -= self._commission * volume

        order = BrokerOrder(
            ticket=self._next_ticket,
            symbol=symbol,
            side=side,
            volume=volume,
            entry_price=fill,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="open",
        )
        self._orders[self._next_ticket] = order
        self._next_ticket += 1
        self._recompute_equity()
        return order

    def close_order(self, ticket: int) -> bool:
        o = self._orders.get(ticket)
        if o is None or o.status != "open":
            return False
        price = self._prices.get(o.symbol, o.entry_price)
        if o.side == "buy":
            pnl = (price - o.entry_price) * o.volume
        else:
            pnl = (o.entry_price - price) * o.volume
        self._balance += pnl - self._commission * o.volume
        o.status = "closed"
        self._recompute_equity()
        return True

    def open_orders(self) -> List[BrokerOrder]:
        return [o for o in self._orders.values() if o.status == "open"]

    def all_orders(self) -> List[BrokerOrder]:
        return list(self._orders.values())
