"""Paper Trader - ported from HFT_Brain.

Simulates trade execution with intrabar SL-before-TP resolution.
Accepts any verdict object with: final_decision, ts, symbol, mode,
debate_winner, risk (with position_size_qty, stop_loss_price,
take_profit_price, risk_amount_usd).
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Callable
from loguru import logger


@dataclass
class PaperTrade:
    id: int
    verdict_ts: int
    symbol: str
    mode: str
    account_type: str
    direction: str
    entry_price: float
    qty: float
    sl: float
    tp: float
    risk_usd: float
    open_ts: int
    max_hold_bars: int = 0
    contributing_strategies: List[str] = field(default_factory=list)
    regime: str = ""
    status: str = "OPEN"
    exit_price: float = 0.0
    close_ts: int = 0
    bars_held: int = 0
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class PaperTrader:
    def __init__(
        self,
        account_type: str,
        starting_balance: float = 10000.0,
        on_trade_close: Optional[Callable[[float], None]] = None,
    ):
        self.account_type = account_type
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.peak_balance = starting_balance
        self.on_trade_close = on_trade_close
        self.open_trades: List[PaperTrade] = []
        self.closed_trades: List[PaperTrade] = []
        self.trade_counter = 0
        logger.info(f"PaperTrader[{account_type}] init | balance=${starting_balance:.2f}")

    def open_positions_count(self, mode: str) -> int:
        return sum(1 for t in self.open_trades if t.mode == mode)

    def total_open_risk_usd(self) -> float:
        return sum(t.risk_usd for t in self.open_trades)

    def can_open(self, mode: str, max_positions: int) -> bool:
        return self.open_positions_count(mode) < max_positions

    def open_trade(
        self,
        verdict,
        candles: List[dict],
        max_hold_bars: int = 0,
        contributing_strategies: Optional[List[str]] = None,
        regime: str = "",
    ) -> Optional[PaperTrade]:
        if verdict.final_decision != "APPROVED":
            return None
        if not candles:
            return None
        entry_candle = candles[-1]
        entry_price = float(entry_candle["close"])
        open_ts = int(entry_candle.get("open_time", 0))
        risk = verdict.risk
        direction = "BUY" if verdict.debate_winner in ("BUY", "LONG") else "SELL"

        self.trade_counter += 1
        trade = PaperTrade(
            id=self.trade_counter,
            verdict_ts=int(verdict.ts),
            symbol=verdict.symbol,
            mode=verdict.mode,
            account_type=self.account_type,
            direction=direction,
            entry_price=entry_price,
            qty=float(risk.position_size_qty),
            sl=float(risk.stop_loss_price),
            tp=float(risk.take_profit_price),
            risk_usd=float(risk.risk_amount_usd),
            open_ts=open_ts,
            max_hold_bars=max_hold_bars,
            contributing_strategies=list(contributing_strategies or []),
            regime=regime,
        )
        self.open_trades.append(trade)
        logger.success(
            f"[{self.account_type}/{trade.mode}] OPEN #{trade.id} "
            f"{trade.direction} qty={trade.qty:.6f} @ {entry_price:.2f} "
            f"SL={trade.sl:.2f} TP={trade.tp:.2f}"
        )
        return trade

    def process_candle(self, candle: dict) -> List[PaperTrade]:
        if not self.open_trades:
            return []
        high = float(candle["high"])
        low = float(candle["low"])
        close_price = float(candle["close"])
        close_ts = int(candle.get("open_time", 0))
        closed_now: List[PaperTrade] = []

        for trade in list(self.open_trades):
            exit_price = None
            status = None
            if trade.direction == "BUY":
                if low <= trade.sl:
                    exit_price = trade.sl; status = "CLOSED_SL"
                elif high >= trade.tp:
                    exit_price = trade.tp; status = "CLOSED_TP"
            else:
                if high >= trade.sl:
                    exit_price = trade.sl; status = "CLOSED_SL"
                elif low <= trade.tp:
                    exit_price = trade.tp; status = "CLOSED_TP"

            trade.bars_held += 1
            if exit_price is None and trade.max_hold_bars > 0:
                if trade.bars_held >= trade.max_hold_bars:
                    exit_price = close_price
                    status = "CLOSED_TIMEOUT"
            if exit_price is None:
                continue

            if trade.direction == "BUY":
                pnl = (exit_price - trade.entry_price) * trade.qty
            else:
                pnl = (trade.entry_price - exit_price) * trade.qty

            trade.status = status
            trade.exit_price = exit_price
            trade.close_ts = close_ts
            trade.pnl_usd = pnl
            trade.pnl_pct = (pnl / self.balance * 100) if self.balance > 0 else 0.0
            self.balance += pnl
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance

            if self.on_trade_close:
                try:
                    self.on_trade_close(pnl)
                except Exception as e:
                    logger.warning(f"on_trade_close callback error: {e}")

            closed_now.append(trade)
            logger.info(
                f"[{self.account_type}/{trade.mode}] CLOSE #{trade.id} "
                f"{status} pnl=${pnl:.2f} bal=${self.balance:.2f}"
            )

        for t in closed_now:
            self.open_trades.remove(t)
            self.closed_trades.append(t)
        return closed_now

    def close_all_at_price(self, candle: dict) -> None:
        if not self.open_trades:
            return
        close_price = float(candle["close"])
        close_ts = int(candle.get("open_time", 0))
        logger.info(f"[{self.account_type}] EOD close {len(self.open_trades)} open trades")
        for trade in list(self.open_trades):
            if trade.direction == "BUY":
                pnl = (close_price - trade.entry_price) * trade.qty
            else:
                pnl = (trade.entry_price - close_price) * trade.qty
            trade.status = "CLOSED_EOD"
            trade.exit_price = close_price
            trade.close_ts = close_ts
            trade.pnl_usd = pnl
            trade.pnl_pct = (pnl / self.balance * 100) if self.balance > 0 else 0.0
            self.balance += pnl
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            if self.on_trade_close:
                try:
                    self.on_trade_close(pnl)
                except Exception as e:
                    logger.warning(f"on_trade_close callback error: {e}")
            self.closed_trades.append(trade)
        self.open_trades.clear()

    def get_stats(self) -> Dict[str, Any]:
        trades = self.closed_trades
        total = len(trades)
        wins = [t for t in trades if t.pnl_usd > 0]
        losses = [t for t in trades if t.pnl_usd < 0]
        flat = [t for t in trades if t.pnl_usd == 0]
        gross_profit = sum(t.pnl_usd for t in wins)
        gross_loss = abs(sum(t.pnl_usd for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        equity = [self.starting_balance]
        for t in trades:
            equity.append(equity[-1] + t.pnl_usd)
        peak = equity[0]; max_dd = 0.0; max_dd_pct = 0.0
        for e in equity:
            if e > peak: peak = e
            dd = peak - e
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = (dd / peak * 100) if peak > 0 else 0.0

        tp_count = sum(1 for t in trades if t.status == "CLOSED_TP")
        sl_count = sum(1 for t in trades if t.status == "CLOSED_SL")
        to_count = sum(1 for t in trades if t.status == "CLOSED_TIMEOUT")
        eod_count = sum(1 for t in trades if t.status == "CLOSED_EOD")

        return {
            "account_type": self.account_type,
            "starting_balance": round(self.starting_balance, 2),
            "ending_balance": round(self.balance, 2),
            "net_pnl": round(self.balance - self.starting_balance, 2),
            "total_trades": total,
            "wins": len(wins), "losses": len(losses), "flat": len(flat),
            "win_rate": round(len(wins) / total * 100, 2) if total > 0 else 0.0,
            "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else "inf",
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_win": round(gross_profit / len(wins), 2) if wins else 0.0,
            "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0.0,
            "max_drawdown_usd": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "peak_balance": round(self.peak_balance, 2),
            "exits_tp": tp_count, "exits_sl": sl_count,
            "exits_timeout": to_count, "exits_eod": eod_count,
        }
