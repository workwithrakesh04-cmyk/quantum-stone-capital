"""Technical indicators for ML feature engineering."""
from typing import List
import numpy as np


def rsi(prices: List[float], period: int = 14) -> float:
    """Relative Strength Index (Wilder)."""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def sma(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return float("nan")
    return float(np.mean(prices[-period:]))


def ema(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return float("nan")
    k = 2.0 / (period + 1)
    val = float(np.mean(prices[:period]))
    for p in prices[period:]:
        val = (p - val) * k + val
    return val


def macd(prices: List[float], fast: int = 12, slow: int = 26) -> float:
    """Returns MACD line (fast EMA - slow EMA)."""
    if len(prices) < slow:
        return 0.0
    return ema(prices, fast) - ema(prices, slow)


def bollinger_bands(prices: List[float], period: int = 20, n_std: float = 2.0) -> dict:
    if len(prices) < period:
        return {"upper": float("nan"), "middle": float("nan"), "lower": float("nan")}
    window = prices[-period:]
    m = float(np.mean(window))
    s = float(np.std(window, ddof=1))
    return {"upper": m + n_std * s, "middle": m, "lower": m - n_std * s}


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(highs) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(highs)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(pc - l)))
    atr_val = float(np.mean(trs[:period]))
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val
