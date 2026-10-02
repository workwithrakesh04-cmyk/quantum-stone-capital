"""D8 Shadow Analysis.

Reads logs/shadow/YYYY-MM-DD.jsonl (written by scripts/shadow_run.py)
and computes the same metrics D8c-3 reported, from the SHADOW data.

Two output modes:
  1. load_shadow_day(day) -> structured dict with:
       - trades: list of closed-trade dicts (from PaperTrader state)
       - decisions: full list of per-candle log records
       - stats: derived headline metrics (Sharpe/Sortino/Calmar/...)
  2. print_comparison(shadow_stats, reference_stats) -> prints a
     side-by-side table of D8c-3 (in-sample) vs D8 (shadow).

Design: reads the JSONL, extracts embedded verdict dicts from
"opened" records, replays them through a PaperTrader to compute
PnL, then runs those trade returns through performance_metrics.
This mirrors the backtester's math exactly.

D8 scope note: with only 100 out-of-sample candles the shadow
sample is tiny. This module produces numbers but makes no claim
about statistical significance. That judgement belongs to D9 (or
a re-run with a larger sample).
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from beta_brain.shadow_audit import ShadowAudit
from beta_brain.paper_trader import PaperTrader
from beta_brain.performance_metrics import (
    compute_sharpe, compute_sortino, calmar_ratio, infer_periods_per_year,
)


MAX_HOLD_BARS = 12  # matches D8c-3


# ----------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------

def load_shadow_day(day: str,
                    run_id: Optional[str] = None) -> Dict[str, Any]:
    """Read one shadow day. Returns {"decisions": [...], "day": str}.

    If run_id is provided, only records with that run_id are returned.
    """
    audit = ShadowAudit()
    decisions = audit.read_day(day)
    if run_id:
        decisions = [d for d in decisions if d.get("run_id") == run_id]
    return {"day": day, "decisions": decisions, "run_id": run_id}


def load_shadow_newest(run_id: Optional[str] = None) -> Dict[str, Any]:
    audit = ShadowAudit()
    day = audit.newest_active_day(min_size=1)
    if day is None:
        return {"day": None, "decisions": [], "run_id": run_id}
    return load_shadow_day(day, run_id=run_id)


def list_runs(day: str) -> List[str]:
    """Return run_ids present in a day's log, in order of appearance."""
    audit = ShadowAudit()
    records = audit.read_day(day)
    seen = []
    for r in records:
        rid = r.get("run_id")
        if rid and rid not in seen:
            seen.append(rid)
    return seen


# ----------------------------------------------------------------------
# Replay: rebuild trades from the shadow decisions
# ----------------------------------------------------------------------

def _mk_verdict_from_dict(v: Dict[str, Any]):
    """Rebuild a minimal object shaped like a JuryVerdict from its
    to_dict() output. Only the fields PaperTrader and the metrics
    need are set."""
    from types import SimpleNamespace

    risk = SimpleNamespace(
        position_size_qty=float(v["risk"]["position_size_qty"]),
        stop_loss_price=float(v["risk"]["stop_loss_price"]),
        take_profit_price=float(v["risk"]["take_profit_price"]),
        risk_amount_usd=float(v["risk"]["risk_amount_usd"]),
    )
    return SimpleNamespace(
        final_decision=v["final_decision"],
        ts=int(v["ts"]),
        symbol=v["symbol"],
        mode=v["mode"],
        debate_winner=v["debate_winner"],
        risk=risk,
    )


def replay_trades(decisions: List[Dict[str, Any]],
                  starting_balance: float = 10000.0) -> List[Dict[str, Any]]:
    """Reconstruct the closed-trade list from a shadow decision log.

    The shadow_run already ran a PaperTrader, but its state is gone.
    We re-run one here from the logged candles to recompute PnL.
    """
    # Extract the price series from the decisions (each has close + open_time)
    # Prefer full OHLC when logged (D8 fidelity); fall back to close
    # as a proxy for older shadow logs that only recorded candle_close.
    def _row(d):
        c = float(d["candle_close"])
        return {
            "close": c,
            "open": float(d.get("candle_open", c)),
            "high": float(d.get("candle_high", c)),
            "low": float(d.get("candle_low", c)),
            "open_time": int(d["candle_open_time"]),
        }
    price_series = [_row(d) for d in decisions]
    if not price_series:
        return []

    trader = PaperTrader(
        account_type="personal",
        starting_balance=starting_balance,
    )
    idx = 0
    for d in decisions:
        candle = price_series[idx]
        trader.process_candle(candle)

        if d.get("note") == "hard_stop":
            trader.close_all_at_price(candle)
            idx += 1
            continue
        if d.get("note") == "halted_skip":
            idx += 1
            continue

        v = d.get("verdict")
        if d.get("note") == "opened" and v:
            try:
                verdict_obj = _mk_verdict_from_dict(v)
                trader.open_trade(
                    verdict_obj,
                    [candle],
                    max_hold_bars=MAX_HOLD_BARS,
                    contributing_strategies=[],
                    regime="SHADOW",
                )
            except Exception:
                pass
        idx += 1

    # Close remainder
    if trader.open_trades:
        trader.close_all_at_price(price_series[-1])

    return [t.to_dict() for t in trader.closed_trades]


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def _returns_from_trades(trades: List[Dict[str, Any]]) -> List[float]:
    returns = []
    for t in trades:
        notional = float(t["entry_price"]) * float(t["qty"])
        if notional > 0:
            returns.append(float(t["pnl_usd"]) / notional)
    return returns


def compute_metrics(trades: List[Dict[str, Any]],
                    starting_balance: float,
                    period_days: Optional[float] = None) -> Dict[str, Any]:
    """Compute D8c-3-style metrics from a list of closed trades."""
    total = len(trades)
    wins = [t for t in trades if t["pnl_usd"] > 0]
    losses = [t for t in trades if t["pnl_usd"] < 0]
    gross_profit = sum(t["pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["pnl_usd"] for t in losses))
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    ending = starting_balance + sum(t["pnl_usd"] for t in trades)
    net = ending - starting_balance
    ret_pct = (net / starting_balance * 100.0) if starting_balance > 0 else 0.0

    # Max drawdown from the trade-by-trade equity
    equity = [starting_balance]
    for t in trades:
        equity.append(equity[-1] + t["pnl_usd"])
    peak = equity[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for e in equity:
        if e > peak:
            peak = e
        dd = peak - e
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0

    returns = _returns_from_trades(trades)
    # Infer periods_per_year from trade frequency when period_days known
    ppy = None
    if period_days and period_days > 0 and total > 0:
        ppy = infer_periods_per_year(total, period_days)

    sharpe = compute_sharpe(returns, periods_per_year=ppy)
    sortino = compute_sortino(returns, 0.0, periods_per_year=ppy)

    stats = {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(ending, 2),
        "net_pnl": round(net, 2),
        "return_pct": round(ret_pct, 2),
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100.0, 2) if total else 0.0,
        "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0.0,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0.0,
        "max_drawdown_usd": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "calmar": round(calmar_ratio({
            "max_drawdown_pct": max_dd_pct,
            "net_pnl": net,
            "starting_balance": starting_balance,
        }), 2),
        "periods_per_year_used": ppy,
    }
    return stats


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------

def _fmt(v, width=12):
    if isinstance(v, str):
        return f"{v:>{width}}"
    if isinstance(v, float):
        return f"{v:>{width}.2f}"
    return f"{v:>{width}}"


def print_comparison(
    shadow_stats: Dict[str, Any],
    reference_stats: Optional[Dict[str, Any]] = None,
    reference_label: str = "D8c-3 (in-sample)",
) -> str:
    """Return a printable side-by-side comparison string."""
    ref = reference_stats or {
        "return_pct": 8.33,
        "total_trades": 102,
        "win_rate": 47.09,
        "profit_factor": 1.361,
        "max_drawdown_pct": 4.67,
        "sharpe": -1.848,       # mean; see D8c3 report for median
        "sortino": None,
        "calmar": None,
    }

    rows = [
        ("return_pct", "Return %"),
        ("total_trades", "Trades"),
        ("win_rate", "Win rate %"),
        ("profit_factor", "Profit factor"),
        ("max_drawdown_pct", "Max DD %"),
        ("sharpe", "Sharpe (mean)"),
        ("sortino", "Sortino"),
        ("calmar", "Calmar"),
    ]

    lines = []
    lines.append("=" * 78)
    lines.append(f"D8 SHADOW vs {reference_label}")
    lines.append("=" * 78)
    lines.append(f"{'Metric':<22} {reference_label:>18} {'D8 shadow':>18}")
    lines.append("-" * 78)
    for key, label in rows:
        rv = ref.get(key)
        sv = shadow_stats.get(key)
        rv_s = "-" if rv is None else str(rv)
        sv_s = "-" if sv is None else str(sv)
        lines.append(f"{label:<22} {rv_s:>18} {sv_s:>18}")
    lines.append("=" * 78)
    lines.append("")
    lines.append("NOTE: D8's shadow sample is small (n trades).")
    lines.append("      Numbers are informational; no statistical claim is made.")
    lines.append("      Real out-of-sample validation requires a larger sample.")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _main():
    import sys
    day = None
    for a in sys.argv[1:]:
        if a.startswith("--day="):
            day = a.split("=", 1)[1]
    if day:
        payload = load_shadow_day(day)
    else:
        payload = load_shadow_newest()

    if not payload["decisions"]:
        print(f"No shadow records found (day={payload['day']}).")
        print("Run scripts/shadow_run.py first.")
        return 1

    trades = replay_trades(payload["decisions"])
    # Compute period_days from the decision log's candle range
    open_times = [int(d["candle_open_time"]) for d in payload["decisions"]]
    if len(open_times) >= 2:
        span_s = (max(open_times) - min(open_times)) / 1000.0
        period_days = max(span_s / 86400.0, 1e-9)
    else:
        period_days = None

    stats = compute_metrics(trades, 10000.0, period_days=period_days)

    print(f"\nDay: {payload['day']}")
    print(f"Decisions: {len(payload['decisions'])}")
    print(f"Replayed trades: {len(trades)}")
    print()
    print(print_comparison(stats))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())