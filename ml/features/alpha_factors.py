"""Alpha factors: momentum, value, quality, volatility."""
from typing import List
import numpy as np


def momentum(prices: List[float], window: int = 20) -> float:
    """Simple momentum: current price / price N bars ago - 1."""
    if len(prices) < window + 1:
        return 0.0
    return (prices[-1] / prices[-window - 1]) - 1.0


def price_acceleration(prices: List[float], short: int = 5, long: int = 20) -> float:
    """Compare recent return to longer return."""
    if len(prices) < long + 1:
        return 0.0
    short_ret = (prices[-1] / prices[-short - 1]) - 1.0
    long_ret = (prices[-1] / prices[-long - 1]) - 1.0
    return short_ret - long_ret


def pct_off_high(prices: List[float], window: int = 252) -> float:
    """Percentage off the rolling high."""
    if len(prices) < 2:
        return 0.0
    window = min(window, len(prices))
    hh = max(prices[-window:])
    if hh == 0:
        return 0.0
    return (prices[-1] - hh) / hh


def volatility_factor(returns: List[float], window: int = 20) -> float:
    """Rolling standard deviation of returns."""
    if len(returns) < window:
        return 0.0
    return float(np.std(returns[-window:], ddof=1))


def low_volatility_score(returns: List[float], window: int = 60) -> float:
    """Inverse vol: higher score = lower volatility."""
    vol = volatility_factor(returns, window)
    if vol <= 0:
        return 0.0
    return 1.0 / vol


def composite_momentum(prices: List[float]) -> float:
    """Average of multiple lookback momentum signals."""
    windows = [5, 10, 20, 60]
    vals = [momentum(prices, w) for w in windows]
    return float(np.mean(vals)) if vals else 0.0
