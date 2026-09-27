"""
Backtest metrics: Sharpe, max drawdown, IC, deflated Sharpe ratio.
"""
from typing import List
import numpy as np


def sharpe_ratio(returns: List[float], rf: float = 0.0, periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    r = np.array(returns, dtype=float)
    excess = r - rf / periods_per_year
    sd = np.std(excess, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(excess) / sd * np.sqrt(periods_per_year))


def max_drawdown(equity: List[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        d = (peak - v) / peak if peak > 0 else 0.0
        if d > dd:
            dd = d
    return dd


def information_coefficient(signal: np.ndarray, forward_return: np.ndarray) -> float:
    """Spearman rank correlation between signal and forward return."""
    if len(signal) < 3 or len(signal) != len(forward_return):
        return 0.0
    from scipy.stats import spearmanr
    ic, _ = spearmanr(signal, forward_return)
    return float(ic) if ic == ic else 0.0


def deflated_sharpe_ratio(sharpe: float, n_trials: int, n_obs: int) -> float:
    """Lopez de Prado's deflated Sharpe ratio (adjusts for multiple testing)."""
    if n_trials <= 1 or n_obs <= 1:
        return sharpe
    from scipy.stats import norm
    euler = 0.5772156649
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    e_max = (1.0 - euler) * z1 + euler * z2
    adjustment = e_max * np.sqrt(1.0 / n_obs)
    return float(sharpe - adjustment)


def calmar_ratio(cagr: float, max_dd: float) -> float:
    if max_dd <= 0:
        return 0.0
    return cagr / max_dd
