"""Performance metrics - ported from HFT_Brain.

Sharpe, Sortino, expectancy, Calmar ratio. Standalone; numpy only.
"""
import math
from typing import List, Dict, Any
import numpy as np


def compute_sharpe(trade_returns: List[float], periods_per_year: int = 105120) -> float:
    if len(trade_returns) < 2:
        return 0.0
    arr = np.array(trade_returns, dtype=np.float64)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def compute_sortino(trade_returns: List[float]) -> float:
    if len(trade_returns) < 2:
        return 0.0
    arr = np.array(trade_returns, dtype=np.float64)
    mean = float(np.mean(arr))
    downside = arr[arr < 0]
    if len(downside) == 0:
        return float("inf") if mean > 0 else 0.0
    downside_std = float(np.std(downside, ddof=1))
    if downside_std == 0:
        return 0.0
    return mean / downside_std


def expectancy(stats: Dict[str, Any]) -> float:
    total = stats.get("total_trades", 0)
    if total == 0:
        return 0.0
    return stats.get("net_pnl", 0.0) / total


def calmar_ratio(stats: Dict[str, Any]) -> float:
    dd_pct = stats.get("max_drawdown_pct", 0.0)
    if dd_pct <= 0:
        return 0.0
    net = stats.get("net_pnl", 0.0)
    start = stats.get("starting_balance", 1.0)
    if start <= 0:
        return 0.0
    return_pct = net / start * 100
    return return_pct / dd_pct


def enrich(stats: Dict[str, Any], trade_returns: List[float]) -> Dict[str, Any]:
    out = dict(stats)
    out["expectancy_usd"] = round(expectancy(stats), 2)
    out["sharpe"] = round(compute_sharpe(trade_returns), 2)
    out["sortino"] = round(compute_sortino(trade_returns), 2)
    out["calmar"] = round(calmar_ratio(stats), 2)
    return out
