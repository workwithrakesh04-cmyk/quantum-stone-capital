"""Shadow Tracker - ported from HFT_Brain.

Observes disabled strategies' would-be signals; simulates hypothetical
trades so we can promote/demote them later.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from loguru import logger


@dataclass
class ShadowTrade:
    strategy: str
    direction: str
    entry_price: float
    entry_ts: int
    sl: float
    tp: float
    regime: str
    outcome: str = "PENDING"
    exit_price: float = 0.0
    exit_ts: int = 0
    bars_held: int = 0
    pnl_pct: float = 0.0


class ShadowTracker:
    def __init__(self, risk_pct: float = 1.0, rr: float = 1.5, atr_mult: float = 1.5):
        self.risk_pct = risk_pct
        self.rr = rr
        self.atr_mult = atr_mult
        self.open_trades: List[ShadowTrade] = []
        self.closed_trades: List[ShadowTrade] = []
        self.stats: Dict[str, Dict[str, int]] = {}
        self.regime_stats: Dict[str, Dict[str, Dict[str, int]]] = {}

    def _atr(self, candles: List[dict], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h = candles[-i]["high"]
            l = candles[-i]["low"]
            pc = candles[-i - 1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        return sum(trs) / len(trs)

    def record_signals(self, signals: List[Any], candles: List[dict], regime: str) -> None:
        if not candles:
            return
        price = candles[-1]["close"]
        ts = candles[-1].get("open_time", 0)
        atr = self._atr(candles)
        if atr <= 0:
            return
        sl_dist = atr * self.atr_mult

        for sig in signals:
            direction = getattr(sig, "direction", None)
            if direction not in ("LONG", "SHORT"):
                continue
            strategy = getattr(sig, "strategy", "unknown")
            if direction == "LONG":
                sl = price - sl_dist; tp = price + sl_dist * self.rr
            else:
                sl = price + sl_dist; tp = price - sl_dist * self.rr
            trade = ShadowTrade(
                strategy=strategy, direction=direction,
                entry_price=price, entry_ts=ts,
                sl=sl, tp=tp, regime=regime,
            )
            self.open_trades.append(trade)

    def process_candle(self, candle: dict) -> None:
        high = candle["high"]
        low = candle["low"]
        ts = candle.get("open_time", 0)
        for trade in list(self.open_trades):
            trade.bars_held += 1
            outcome = None; exit_price = 0.0
            if trade.direction == "LONG":
                if low <= trade.sl:
                    outcome = "LOSS"; exit_price = trade.sl
                elif high >= trade.tp:
                    outcome = "WIN"; exit_price = trade.tp
            else:
                if high >= trade.sl:
                    outcome = "LOSS"; exit_price = trade.sl
                elif low <= trade.tp:
                    outcome = "WIN"; exit_price = trade.tp

            if outcome is None and trade.bars_held >= 12:
                outcome = "TIMEOUT"; exit_price = candle["close"]

            if outcome:
                trade.outcome = outcome
                trade.exit_price = exit_price
                trade.exit_ts = ts
                if trade.direction == "LONG":
                    pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
                else:
                    pnl_pct = (trade.entry_price - exit_price) / trade.entry_price * 100
                trade.pnl_pct = round(pnl_pct, 4)
                self.open_trades.remove(trade)
                self.closed_trades.append(trade)

                s = self.stats.setdefault(
                    trade.strategy,
                    {"wins": 0, "losses": 0, "timeouts": 0, "pnl_pct": 0.0},
                )
                if outcome == "WIN": s["wins"] += 1
                elif outcome == "LOSS": s["losses"] += 1
                else: s["timeouts"] += 1
                s["pnl_pct"] = round(s["pnl_pct"] + pnl_pct, 4)

                rs = self.regime_stats.setdefault(trade.regime, {})
                strat_s = rs.setdefault(
                    trade.strategy,
                    {"wins": 0, "losses": 0, "timeouts": 0, "pnl_pct": 0.0},
                )
                if outcome == "WIN": strat_s["wins"] += 1
                elif outcome == "LOSS": strat_s["losses"] += 1
                else: strat_s["timeouts"] += 1
                strat_s["pnl_pct"] = round(strat_s["pnl_pct"] + pnl_pct, 4)

    def report(self) -> Dict[str, Any]:
        return {
            "strategies": self.stats,
            "regimes": self.regime_stats,
            "open_count": len(self.open_trades),
            "closed_count": len(self.closed_trades),
        }
