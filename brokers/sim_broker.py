"""
SimBroker: our own custom paper-trading broker.
No external dependencies. Tracks balance, equity, positions, P&L.
Designed to work with config/accounts.yaml (personal + prop).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Position:
    ticket: int
    symbol: str
    side: str                    # "buy" | "sell"
    volume: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: Optional[str] = None
    close_price: Optional[float] = None
    pnl: float = 0.0
    status: str = "open"         # "open" | "closed"


@dataclass
class AccountState:
    name: str
    account_type: str            # "retail" | "prop_firm"
    currency: str = "USD"
    starting_balance: float = 10000.0
    balance: float = 10000.0
    equity: float = 10000.0
    peak_equity: float = 10000.0
    margin_used: float = 0.0
    positions: List[Position] = field(default_factory=list)
    closed_positions: List[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.10
    max_concurrent_positions: int = 5
    allow_news_trading: bool = True
    allow_weekend_holding: bool = True
    min_trading_days: int = 0
    profit_target: Optional[float] = None
    notes: str = ""

    @property
    def drawdown_pct(self) -> float:
        if self.peak_equity == 0:
            return 0.0
        return max(0.0, (self.peak_equity - self.equity) / self.peak_equity)

    @property
    def daily_loss_pct(self) -> float:
        return abs(min(self.daily_pnl, 0)) / self.starting_balance

    @property
    def open_positions_count(self) -> int:
        return len([p for p in self.positions if p.status == "open"])

    @property
    def free_margin(self) -> float:
        return self.equity - self.margin_used


class SimBroker:
    """
    Custom paper-trading broker.
    Supports multiple named accounts, each with its own state and rules.
    """

    def __init__(self, commission_per_unit: float = 0.0, slippage_pct: float = 0.0002):
        self.accounts: Dict[str, AccountState] = {}
        self._prices: Dict[str, float] = {}
        self._next_ticket = 1
        self._commission = commission_per_unit
        self._slippage_pct = slippage_pct
        self._connected = False

    # ---------- lifecycle ----------
    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    # ---------- accounts ----------
    def create_account(
        self,
        name: str,
        starting_balance: float,
        account_type: str = "retail",
        **rules,
    ) -> AccountState:
        acc = AccountState(
            name=name,
            account_type=account_type,
            starting_balance=starting_balance,
            balance=starting_balance,
            equity=starting_balance,
            peak_equity=starting_balance,
            max_risk_per_trade=rules.get("max_risk_per_trade", 0.01),
            max_daily_loss=rules.get("max_daily_loss", 0.03),
            max_drawdown=rules.get("max_drawdown", 0.10),
            max_concurrent_positions=rules.get("max_concurrent_positions", 5),
            allow_news_trading=rules.get("allow_news_trading", True),
            allow_weekend_holding=rules.get("allow_weekend_holding", True),
            min_trading_days=rules.get("min_trading_days", 0),
            profit_target=rules.get("profit_target"),
            notes=rules.get("notes", ""),
        )
        self.accounts[name] = acc
        return acc

    def get_account(self, name: str) -> Optional[AccountState]:
        return self.accounts.get(name)

    def account_info(self, name: str) -> Optional[AccountState]:
        return self.accounts.get(name)

    # ---------- prices ----------
    def set_price(self, symbol: str, price: float) -> None:
        self._prices[symbol] = price
        self._recompute_all_equity()

    def last_price(self, symbol: str) -> Optional[float]:
        return self._prices.get(symbol)

    # ---------- trading rules ----------
    def can_open_trade(
        self,
        account_name: str,
        symbol: str,
        risk_amount: float,
        is_news_time: bool = False,
        is_weekend: bool = False,
    ) -> tuple:
        acc = self.accounts.get(account_name)
        if acc is None:
            return False, "unknown_account"

        if symbol not in [s for s in self._prices.keys()] and self.last_price(symbol) is None:
            return False, "no_price_for_symbol"

        max_risk = acc.max_risk_per_trade * acc.starting_balance
        if risk_amount > max_risk:
            return False, "risk_exceeds_limit"

        if acc.daily_loss_pct >= acc.max_daily_loss:
            return False, "daily_loss_limit_hit"

        if acc.drawdown_pct >= acc.max_drawdown:
            return False, "max_drawdown_hit"

        if acc.open_positions_count >= acc.max_concurrent_positions:
            return False, "max_positions"

        if is_news_time and not acc.allow_news_trading:
            return False, "news_trading_not_allowed"

        if is_weekend and not acc.allow_weekend_holding:
            return False, "weekend_holding_not_allowed"

        return True, "OK"

    # ---------- orders ----------
    def open_order(
        self,
        account_name: str,
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        order_type: str = "market",
    ) -> Optional[Position]:
        if not self._connected:
            return None
        acc = self.accounts.get(account_name)
        if acc is None:
            return None
        if side not in ("buy", "sell"):
            return None
        if volume <= 0:
            return None
        price = self._prices.get(symbol)
        if price is None:
            return None

        fill = price * (1 + self._slippage_pct) if side == "buy" else price * (1 - self._slippage_pct)
        acc.balance -= self._commission * volume

        pos = Position(
            ticket=self._next_ticket,
            symbol=symbol,
            side=side,
            volume=volume,
            entry_price=fill,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self._next_ticket += 1
        acc.positions.append(pos)
        acc.margin_used += abs(volume * fill) * 0.01
        self._recompute_equity(acc)
        return pos

    def close_position(self, account_name: str, ticket: int) -> bool:
        acc = self.accounts.get(account_name)
        if acc is None:
            return False
        pos = next((p for p in acc.positions if p.ticket == ticket and p.status == "open"), None)
        if pos is None:
            return False
        price = self._prices.get(pos.symbol, pos.entry_price)
        if pos.side == "buy":
            pnl = (price - pos.entry_price) * pos.volume
        else:
            pnl = (pos.entry_price - price) * pos.volume
        pnl -= self._commission * pos.volume
        acc.balance += pnl
        acc.total_pnl += pnl
        acc.daily_pnl += pnl
        pos.pnl = pnl
        pos.status = "closed"
        pos.close_price = price
        pos.closed_at = datetime.now(timezone.utc).isoformat()
        acc.margin_used = max(0.0, acc.margin_used - abs(pos.volume * pos.entry_price) * 0.01)
        acc.positions.remove(pos)
        acc.closed_positions.append(pos)
        self._recompute_equity(acc)
        return True

    def open_positions(self, account_name: str) -> List[Position]:
        acc = self.accounts.get(account_name)
        if acc is None:
            return []
        return [p for p in acc.positions if p.status == "open"]

    def closed_positions(self, account_name: str) -> List[Position]:
        acc = self.accounts.get(account_name)
        if acc is None:
            return []
        return acc.closed_positions

    # ---------- equity ----------
    def _recompute_equity(self, acc: AccountState) -> None:
        unrealized = 0.0
        for p in acc.positions:
            if p.status != "open":
                continue
            price = self._prices.get(p.symbol, p.entry_price)
            if p.side == "buy":
                unrealized += (price - p.entry_price) * p.volume
            else:
                unrealized += (p.entry_price - price) * p.volume
        acc.equity = acc.balance + unrealized
        if acc.equity > acc.peak_equity:
            acc.peak_equity = acc.equity

    def _recompute_all_equity(self) -> None:
        for acc in self.accounts.values():
            self._recompute_equity(acc)

    # ---------- reporting ----------
    def snapshot(self) -> dict:
        """Return a JSON-friendly snapshot of all accounts."""
        return {
            "accounts": {
                name: {
                    "name": acc.name,
                    "type": acc.account_type,
                    "balance": round(acc.balance, 2),
                    "equity": round(acc.equity, 2),
                    "peak_equity": round(acc.peak_equity, 2),
                    "margin_used": round(acc.margin_used, 2),
                    "free_margin": round(acc.free_margin, 2),
                    "daily_pnl": round(acc.daily_pnl, 2),
                    "total_pnl": round(acc.total_pnl, 2),
                    "daily_loss_pct": round(acc.daily_loss_pct, 4),
                    "drawdown_pct": round(acc.drawdown_pct, 4),
                    "max_risk_per_trade": acc.max_risk_per_trade,
                    "max_daily_loss": acc.max_daily_loss,
                    "max_drawdown": acc.max_drawdown,
                    "max_concurrent_positions": acc.max_concurrent_positions,
                    "open_positions": acc.open_positions_count,
                    "closed_positions": len(acc.closed_positions),
                    "allow_news_trading": acc.allow_news_trading,
                    "allow_weekend_holding": acc.allow_weekend_holding,
                    "profit_target": acc.profit_target,
                    "notes": acc.notes,
                }
                for name, acc in self.accounts.items()
            },
            "prices": dict(self._prices),
        }
