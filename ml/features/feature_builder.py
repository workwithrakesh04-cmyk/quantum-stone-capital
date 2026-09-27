"""
Feature Builder.
Turns a raw OHLCV series into a numeric feature vector for ML models.
"""
from typing import List, Optional
import numpy as np

from ml.features.alpha_factors import (
    momentum, price_acceleration, pct_off_high,
    volatility_factor, low_volatility_score, composite_momentum,
)
from ml.features.technical import (
    rsi, sma, ema, macd, bollinger_bands, atr,
)


class FeatureBuilder:
    """Builds a fixed-length feature vector from OHLCV history."""

    FEATURE_NAMES = [
        "momentum_5",
        "momentum_20",
        "price_accel",
        "pct_off_high",
        "volatility_20",
        "low_vol_score",
        "composite_momentum",
        "rsi_14",
        "sma_20_ratio",
        "sma_50_ratio",
        "ema_20_ratio",
        "macd",
        "bb_position",
        "bb_width",
        "atr_norm",
    ]

    @classmethod
    def build(
        cls,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: Optional[List[float]] = None,
    ) -> np.ndarray:
        """Return a 1-D numpy array of features (or zeros if not enough data)."""
        n = len(cls.FEATURE_NAMES)
        if len(closes) < 60:
            return np.zeros(n, dtype=float)

        returns = list(np.diff(closes) / np.array(closes[:-1]))

        feats = [
            momentum(closes, 5),
            momentum(closes, 20),
            price_acceleration(closes),
            pct_off_high(closes),
            volatility_factor(returns, 20),
            low_volatility_score(returns, 60),
            composite_momentum(closes),
            rsi(closes, 14),
            (closes[-1] / sma(closes, 20)) - 1.0 if sma(closes, 20) else 0.0,
            (closes[-1] / sma(closes, 50)) - 1.0 if sma(closes, 50) else 0.0,
            (closes[-1] / ema(closes, 20)) - 1.0 if ema(closes, 20) else 0.0,
            macd(closes),
        ]

        bb = bollinger_bands(closes)
        if bb["upper"] and bb["upper"] == bb["upper"]:  # not NaN
            span = bb["upper"] - bb["lower"]
            if span > 0:
                feats.append((closes[-1] - bb["lower"]) / span)
            else:
                feats.append(0.5)
            mid = bb["middle"]
            feats.append(span / mid if mid else 0.0)
        else:
            feats.append(0.5)
            feats.append(0.0)

        atr_val = atr(highs, lows, closes)
        feats.append(atr_val / closes[-1] if closes[-1] else 0.0)

        return np.array(feats, dtype=float)
