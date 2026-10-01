"""Performance metrics - ported from HFT_Brain.

Sharpe, Sortino, expectancy, Calmar ratio. Standalone; numpy only.

D6c fixes:
  - compute_sharpe: periods_per_year is now optional and auto-inferred from
    trade count + elapsed period when not supplied. The old default of
    105120 (5m bars per year) massively inflated trade-based Sharpe.
  - compute_sortino: downside deviation is now computed over ALL trades
    relative to MAR (default 0), not std of the losing subset. Annualized
    the same way as Sharpe.
"""
import math
from typing import List, Dict, Any, Optional
import numpy as np


def infer_periods_per_year(total_trades: int, period_days: Optional[float]) -> int:
    """Infer trade-frequency annualization factor.

    If period_days is known and > 0, use trades/period_days * 365.
    Otherwise fall back to a conservative 252 (trading days/year).
    Never returns < 1.
    """
    if period_days and period_days > 0 and total_trades > 0:
        tpy = int(round(total_trades * 365.0 / period_days))
        return max(tpy, 1)
    return 252


def compute_sharpe(
    trade_returns: List[float],
    periods_per_year: Optional[int] = None,
) -> float:
    """Sharpe ratio on per-trade fractional returns.

    periods_per_year:
        - None  -> auto-inferred (falls back to 252)
        - int   -> used as-is
    """
    if len(trade_returns) < 2:
        return 0.0
    arr = np.array(trade_returns, dtype=np.float64)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return 0.0
    ppy = periods_per_year if periods_per_year is not None else 252
    ppy = max(int(ppy), 1)
    return (mean / std) * math.sqrt(ppy)


def compute_sortino(
    trade_returns: List[float],
    mar: float = 0.0,
    periods_per_year: Optional[int] = None,
) -> float:
    """Sortino ratio on per-trade fractional returns.

    Downside deviation is computed over ALL trades relative to MAR:
        dd = sqrt( mean( min(0, r - mar)^2 ) )
    """
    if len(trade_returns) < 2:
        return 0.0
    arr = np.array(trade_returns, dtype=np.float64)
    mean = float(np.mean(arr))
    excess = arr - mar
    downside = np.minimum(excess, 0.0)
    dd = float(np.sqrt(np.mean(downside ** 2)))
    if dd == 0:
        return float("inf") if mean > mar else 0.0
    ppy = periods_per_year if periods_per_year is not None else 252
    ppy = max(int(ppy), 1)
    return ((mean - mar) / dd) * math.sqrt(ppy)


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


def enrich(
    stats: Dict[str, Any],
    trade_returns: List[float],
    periods_per_year: Optional[int] = None,
    period_days: Optional[float] = None,
) -> Dict[str, Any]:
    """Attach expectancy / Sharpe / Sortino / Calmar.

    If periods_per_year is None, it is inferred from stats['total_trades']
    and period_days (when supplied).
    """
    out = dict(stats)
    if periods_per_year is None:
        total = int(stats.get("total_trades", 0))
        periods_per_year = infer_periods_per_year(total, period_days)
    out["expectancy_usd"] = round(expectancy(stats), 2)
    out["sharpe"] = round(compute_sharpe(trade_returns, periods_per_year), 2)
    out["sortino"] = round(compute_sortino(trade_returns, 0.0, periods_per_year), 2)
    out["calmar"] = round(calmar_ratio(stats), 2)
    out["periods_per_year_used"] = int(periods_per_year)
    return out