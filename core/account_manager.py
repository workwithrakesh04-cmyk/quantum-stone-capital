"""
Account Manager - Layer 1
Enforces CCP-equivalent rules + prop firm rules + Wyckoff risk rules.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from datetime import date
import yaml


@dataclass
class AccountState:
    name: str
    capital: float
    equity: float
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    peak_equity: float = 0.0
    open_positions: List[dict] = field(default_factory=list)
    trades_today: int = 0
    losses_today: int = 0
    last_reset: date = field(default_factory=date.today)

    @property
    def drawdown(self) -> float:
        if self.peak_equity == 0:
            return 0.0
        return (self.peak_equity - self.equity) / self.peak_equity

    @property
    def daily_loss_pct(self) -> float:
        return abs(min(self.daily_pnl, 0)) / self.capital


class AccountManager:
    """Manages personal + prop accounts with CCP-equivalent rules."""

    def __init__(self, config_path: str = "config/master.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.accounts: Dict[str, AccountState] = {}
        self._init_accounts()

    def _init_accounts(self):
        for name, cfg in self.config["accounts"].items():
            self.accounts[name] = AccountState(
                name=name,
                capital=cfg["capital"],
                equity=cfg["capital"],
                peak_equity=cfg["capital"],
            )

    def _reset_daily_if_needed(self, account: AccountState):
        today = date.today()
        if account.last_reset != today:
            account.daily_pnl = 0.0
            account.trades_today = 0
            account.losses_today = 0
            account.last_reset = today

    def can_open_trade(
        self, account_name: str, risk_amount: float, instrument: str
    ) -> Tuple[bool, str]:
        """CCP-equivalent pre-trade check. Returns (allowed, reason)."""
        acc = self.accounts[account_name]
        cfg = self.config["accounts"][account_name]
        self._reset_daily_if_needed(acc)

        if instrument not in cfg.get("instruments", []):
            return False, f"{instrument} not in allowed instruments"

        max_risk = cfg["max_risk_per_trade"] * acc.capital
        if risk_amount > max_risk:
            return False, f"Risk ${risk_amount:.2f} > max ${max_risk:.2f}"

        if acc.daily_loss_pct >= cfg["max_daily_loss"]:
            return False, f"Daily loss {acc.daily_loss_pct:.2%} >= limit {cfg['max_daily_loss']:.2%}"

        if acc.drawdown >= cfg["max_drawdown"]:
            return False, f"Drawdown {acc.drawdown:.2%} >= limit {cfg['max_drawdown']:.2%}"

        if len(acc.open_positions) >= cfg.get("max_concurrent_positions", 5):
            return False, "Max concurrent positions reached"

        max_losses = self.config["risk"].get("max_losses_per_day", 2)
        if acc.losses_today >= max_losses:
            return False, f"Max losses/day ({max_losses}) reached"

        return True, "OK"

    def register_trade(self, account_name: str, pnl: float):
        """Update account state after trade close."""
        acc = self.accounts[account_name]
        self._reset_daily_if_needed(acc)
        acc.daily_pnl += pnl
        acc.total_pnl += pnl
        acc.equity += pnl
        acc.trades_today += 1
        if pnl < 0:
            acc.losses_today += 1
        if acc.equity > acc.peak_equity:
            acc.peak_equity = acc.equity

    def get_status(self, account_name: str) -> dict:
        acc = self.accounts[account_name]
        return {
            "name": acc.name,
            "capital": acc.capital,
            "equity": acc.equity,
            "daily_pnl": acc.daily_pnl,
            "daily_loss_pct": acc.daily_loss_pct,
            "drawdown": acc.drawdown,
            "open_positions": len(acc.open_positions),
            "trades_today": acc.trades_today,
            "losses_today": acc.losses_today,
        }
