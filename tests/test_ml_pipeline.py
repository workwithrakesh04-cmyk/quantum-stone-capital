"""Tests for the ML pipeline and its components."""
import numpy as np
import pytest

from ml.features.alpha_factors import momentum, volatility_factor, composite_momentum
from ml.features.technical import rsi, sma, ema, macd, bollinger_bands, atr
from ml.features.feature_builder import FeatureBuilder
from ml.backtest.walk_forward import walk_forward_splits, combinatorial_splits
from ml.backtest.metrics import (
    sharpe_ratio, max_drawdown, information_coefficient, deflated_sharpe_ratio,
)
from ml.pipeline import MLPipeline


def test_momentum_positive():
    prices = list(range(100, 130))
    assert momentum(prices, 5) > 0


def test_volatility_factor_positive():
    returns = [0.01, -0.005, 0.02, -0.015, 0.01] * 10
    assert volatility_factor(returns, 20) > 0


def test_composite_momentum_shape():
    prices = list(range(100, 200))
    assert isinstance(composite_momentum(prices), float)


def test_rsi_uptrend_high():
    prices = list(range(100, 130))
    assert rsi(prices, 14) > 70


def test_sma_correct():
    prices = [1, 2, 3, 4, 5]
    assert sma(prices, 5) == 3.0


def test_ema_returns_float():
    prices = list(range(100, 200))
    assert isinstance(ema(prices, 20), float)


def test_macd_zero_on_flat():
    prices = [100.0] * 60
    assert abs(macd(prices)) < 1e-6


def test_bollinger_bands_shape():
    prices = list(range(100, 130))
    bb = bollinger_bands(prices, 20)
    assert bb["upper"] > bb["middle"] > bb["lower"]


def test_atr_positive():
    highs = [10 + i * 0.5 for i in range(30)]
    lows = [9 + i * 0.5 for i in range(30)]
    closes = [9.5 + i * 0.5 for i in range(30)]
    assert atr(highs, lows, closes, 14) > 0


def test_feature_builder_vector_shape():
    np.random.seed(42)
    closes = list(np.cumsum(np.random.randn(120)) + 100)
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    feats = FeatureBuilder.build(closes, highs, lows)
    assert feats.shape == (len(FeatureBuilder.FEATURE_NAMES),)


def test_feature_builder_zero_on_short_history():
    closes = [100.0] * 10
    highs = [101.0] * 10
    lows = [99.0] * 10
    feats = FeatureBuilder.build(closes, highs, lows)
    assert np.all(feats == 0)


def test_walk_forward_splits_count():
    splits = list(walk_forward_splits(n_samples=1000, train_size=200,
                                     test_size=50, purge=5, embargo=5))
    assert len(splits) > 0


def test_combinatorial_splits_count():
    splits = list(combinatorial_splits(n_samples=500, n_splits=5))
    assert len(splits) == 5


def test_sharpe_ratio_positive():
    returns = [0.01, 0.02, -0.005, 0.015, 0.01, 0.005] * 10
    assert sharpe_ratio(returns) > 0


def test_max_drawdown_known():
    equity = [100, 110, 105, 120, 90, 100]
    assert abs(max_drawdown(equity) - 0.25) < 1e-3


def test_information_coefficient_perfect():
    signal = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    fwd = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    assert abs(information_coefficient(signal, fwd) - 1.0) < 1e-6


def test_deflated_sharpe_reduces():
    assert deflated_sharpe_ratio(1.5, n_trials=100, n_obs=500) < 1.5


def test_pipeline_rejects_unknown_model():
    with pytest.raises(ValueError):
        MLPipeline(model_type="not_a_model")


def test_pipeline_build_features_shape():
    np.random.seed(0)
    closes = list(np.cumsum(np.random.randn(200)) + 100)
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    X = MLPipeline.build_features(closes, highs, lows)
    assert X.shape[1] == len(FeatureBuilder.FEATURE_NAMES)
    assert X.shape[0] > 0
