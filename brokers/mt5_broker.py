"""
MetaTrader 5 broker adapter.
Requires: pip install MetaTrader5 (Windows only) + MT5 terminal running.
Gracefully degrades on non-Windows or when MT5 is not installed.
"""
from typing import Dict, List, Optional

from brokers.base_broker import BaseBroker, BrokerOrder, BrokerAccount


class MT5Broker(BaseBroker):
    name = "mt5"

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None,
        magic: int = 20260101,
    ):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.magic = magic
        self._mt5 = None
        self._connected = False

    # --- lifecycle ---
    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5  # noqa: F401
        except ImportError:
            print("MT5Broker: MetaTrader5 not installed (pip install MetaTrader5)")
            return False

        self._mt5 = mt5

        if self.path:
            init_ok = mt5.initialize(self.path, login=self.login,
                                     password=self.password, server=self.server)
        else:
            init_ok = mt5.initialize()

        if not init_ok:
            print("MT5Broker: initialize failed:", mt5.last_error())
            return False

        self._connected = True
        return True

    def disconnect(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
        self._connected = False

    # --- account ---
    def account_info(self) -> BrokerAccount:
        if not self._connected:
            return BrokerAccount(0.0, 0.0, 0.0, 0.0)
        info = self._mt5.account_info()
        if info is None:
            return BrokerAccount(0.0, 0.0, 0.0, 0.0)
        return BrokerAccount(
            balance=float(info.balance),
            equity=float(info.equity),
            margin=float(info.margin),
            free_margin=float(info.margin_free),
            currency=str(info.currency),
        )

    # --- prices ---
    def last_price(self, symbol: str) -> Optional[float]:
        if not self._connected:
            return None
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return float((tick.bid + tick.ask) / 2.0)

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
        mt5 = self._mt5

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        if side == "buy":
            price = tick.ask
            mt5_type = mt5.ORDER_TYPE_BUY
        elif side == "sell":
            price = tick.bid
            mt5_type = mt5.ORDER_TYPE_SELL
        else:
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": mt5_type,
            "price": float(price),
            "sl": float(stop_loss) if stop_loss else 0.0,
            "tp": float(take_profit) if take_profit else 0.0,
            "deviation": 10,
            "magic": self.magic,
            "comment": "qsc-brain",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            print("MT5Broker: order failed:", result)
            return None

        return BrokerOrder(
            ticket=int(result.order),
            symbol=symbol,
            side=side,
            volume=float(volume),
            entry_price=float(result.price),
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="open",
        )

    def close_order(self, ticket: int) -> bool:
        if not self._connected:
            return False
        mt5 = self._mt5
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        pos = positions[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": float(pos.volume),
            "type": close_type,
            "position": int(ticket),
            "price": float(price),
            "deviation": 10,
            "magic": self.magic,
            "comment": "qsc-brain-close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

    def open_orders(self) -> List[BrokerOrder]:
        if not self._connected:
            return []
        positions = self._mt5.positions_get()
        if positions is None:
            return []
        out = []
        for p in positions:
            out.append(BrokerOrder(
                ticket=int(p.ticket),
                symbol=str(p.symbol),
                side="buy" if p.type == 0 else "sell",
                volume=float(p.volume),
                entry_price=float(p.price_open),
                stop_loss=float(p.sl) if p.sl else None,
                take_profit=float(p.tp) if p.tp else None,
                status="open",
            ))
        return out
