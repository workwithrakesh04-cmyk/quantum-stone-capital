"""
Math utilities for the trading brain.
Z-score, rolling stats, ATR, normalization helpers.
"""
from typing import List, Optional
import numpy as np


def z_score(value: float, mean: float, std: float) -> float:
    """Standard z-score; returns 0 if std is 0."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def rolling_mean(values: List[float], window: int) -> float:
    """Mean of the last `window` values."""
    if len(values) < window:
        return float("nan")
    return float(np.mean(values[-window:]))


def rolling_std(values: List[float], window: int, ddof: int = 1) -> float:
    """Standard deviation of the last `window` values."""
    if len(values) < window:
        return float("nan")
    return float(np.std(values[-window:], ddof=ddof))


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range using Wilder's smoothing."""
    if len(highs) < period + 1:
        return float("nan")

    trs = []
    for i in range(1, len(highs)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - pc), abs(pc - l))
        trs.append(tr)

    if len(trs) < period:
        return float("nan")

    # Wilder's smoothing: first ATR is SMA of first period TRs
    atr_val = float(np.mean(trs[:period]))
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def true_range(high: float, low: float, prev_close: float) -> float:
    """Single-bar true range."""
    return max(high - low, abs(high - prev_close), abs(prev_close - low))


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalize to [0, 1]."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def pct_change(new: float, old: float) -> float:
    """Percent change from old → new. Returns 0 if old is 0."""
    if old == 0:
        return 0.0
    return (new - old) / old


def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Annualized Sharpe ratio from a list of periodic returns."""
    if len(returns) < 2:
        return 0.0
    r = np.array(returns, dtype=float)
    excess = r - risk_free_rate / periods_per_year
    if np.std(excess, ddof=1) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: List[float]) -> float:
    """Maximum peak-to-trough drawdown as a fraction (0.0 to 1.0)."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd
