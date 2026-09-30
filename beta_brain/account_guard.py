"""Account Guard - ported from HFT_Brain.

Daily-time-based reset, kill switch, consecutive-loss scaling.
Independent from QSC's core/prop_rules.py.
"""
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class AccountState:
    starting_balance: float
    current_balance: float
    peak_balance: float
    daily_start_balance: float
    daily_trades: int = 0
    consecutive_losses: int = 0
    kill_switch_triggered: bool = False
    kill_reason: str = ""
    last_reset_day: int = 0
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "daily_start_balance": self.daily_start_balance,
            "daily_trades": self.daily_trades,
            "consecutive_losses": self.consecutive_losses,
            "kill_switch_triggered": self.kill_switch_triggered,
            "kill_reason": self.kill_reason,
            "last_reset_day": self.last_reset_day,
            "warnings": self.warnings,
        }


class AccountGuard:
    def __init__(self, config: dict):
        rules = config.get("account_rules", {})
        self.account_type = config.get("account", {}).get("account_type", "personal")
        self.max_daily_loss_pct = rules.get("max_daily_loss_pct", 5.0)
        self.max_total_dd_pct = rules.get("max_total_drawdown_pct", 10.0)
        self.enable_kill_switch = rules.get("enable_kill_switch", self.account_type == "prop")
        self.starting_balance = config["account"]["starting_balance"]
        self.daily_limits = config.get("daily_limits", {})
        self.max_daily_trades = self.daily_limits.get("max_daily_trades", 10)
        self.max_consecutive_losses = self.daily_limits.get("disable_after_consecutive_losses", 3)

        self.state = AccountState(
            starting_balance=self.starting_balance,
            current_balance=self.starting_balance,
            peak_balance=self.starting_balance,
            daily_start_balance=self.starting_balance,
            last_reset_day=0,
        )
        logger.info(
            f"AccountGuard[{self.account_type}]: "
            f"daily_limit={self.max_daily_loss_pct}% "
            f"dd_limit={self.max_total_dd_pct}% "
            f"max_daily_trades={self.max_daily_trades} "
            f"kill_switch={'ON' if self.enable_kill_switch else 'OFF'}"
        )

    def _day_from_ts(self, ts_ms: int) -> int:
        return ts_ms // 86400000

    def daily_reset_if_needed(self, current_ts_ms: Optional[int] = None) -> None:
        if current_ts_ms is None:
            return
        day = self._day_from_ts(current_ts_ms)
        if day != self.state.last_reset_day:
            logger.debug(
                f"AccountGuard[{self.account_type}]: daily reset "
                f"(day {self.state.last_reset_day} -> {day})"
            )
            self.state.daily_start_balance = self.state.current_balance
            self.state.daily_trades = 0
            self.state.consecutive_losses = 0
            self.state.last_reset_day = day
            self.state.warnings = []

    def check(self, current_ts_ms: Optional[int] = None):
        if current_ts_ms is not None:
            self.daily_reset_if_needed(current_ts_ms)

        if self.state.kill_switch_triggered:
            return False, f"kill switch: {self.state.kill_reason}"

        if self.state.daily_start_balance > 0:
            daily_pnl_pct = (
                (self.state.current_balance - self.state.daily_start_balance)
                / self.state.daily_start_balance * 100
            )
            if daily_pnl_pct <= -self.max_daily_loss_pct:
                reason = f"daily loss {daily_pnl_pct:.2f}% hit limit -{self.max_daily_loss_pct}%"
                if self.enable_kill_switch:
                    self._trigger_kill(reason)
                    return False, reason
                else:
                    if reason not in self.state.warnings:
                        self.state.warnings.append(reason)
                    return True, "ok (warned)"

        if self.state.peak_balance > 0:
            dd_pct = (
                (self.state.peak_balance - self.state.current_balance)
                / self.state.peak_balance * 100
            )
            if dd_pct >= self.max_total_dd_pct:
                reason = f"total DD {dd_pct:.2f}% hit limit {self.max_total_dd_pct}%"
                if self.enable_kill_switch:
                    self._trigger_kill(reason)
                    return False, reason
                else:
                    if reason not in self.state.warnings:
                        self.state.warnings.append(reason)
                    return True, "ok (warned)"

        if self.state.daily_trades >= self.max_daily_trades:
            return False, f"daily trade limit {self.max_daily_trades} reached"

        if self.state.consecutive_losses >= self.max_consecutive_losses:
            return False, f"{self.state.consecutive_losses} consecutive losses"

        return True, "ok"

    def _trigger_kill(self, reason: str) -> None:
        self.state.kill_switch_triggered = True
        self.state.kill_reason = reason
        logger.critical(f"KILL SWITCH [{self.account_type}]: {reason}")

    def record_trade(self, pnl_usd: float) -> None:
        self.state.current_balance += pnl_usd
        if self.state.current_balance > self.state.peak_balance:
            self.state.peak_balance = self.state.current_balance
        self.state.daily_trades += 1
        if pnl_usd < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

    def snapshot(self) -> dict:
        daily_pnl = self.state.current_balance - self.state.daily_start_balance
        daily_pnl_pct = (daily_pnl / self.state.daily_start_balance * 100) if self.state.daily_start_balance else 0
        total_dd = self.state.peak_balance - self.state.current_balance
        total_dd_pct = (total_dd / self.state.peak_balance * 100) if self.state.peak_balance else 0
        return {
            "account_type": self.account_type,
            "starting_balance": self.state.starting_balance,
            "current_balance": round(self.state.current_balance, 2),
            "peak_balance": round(self.state.peak_balance, 2),
            "daily_pnl_usd": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "total_dd_usd": round(total_dd, 2),
            "total_dd_pct": round(total_dd_pct, 2),
            "daily_trades": self.state.daily_trades,
            "consecutive_losses": self.state.consecutive_losses,
            "kill_switch_triggered": self.state.kill_switch_triggered,
            "kill_reason": self.state.kill_reason,
            "warnings": self.state.warnings,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_total_dd_pct": self.max_total_dd_pct,
        }


_guards: dict = {}


def get_account_guard(config: dict) -> AccountGuard:
    account_type = config.get("account", {}).get("account_type", "personal")
    if account_type not in _guards:
        _guards[account_type] = AccountGuard(config)
    return _guards[account_type]


def reset_guards() -> None:
    global _guards
    _guards = {}
