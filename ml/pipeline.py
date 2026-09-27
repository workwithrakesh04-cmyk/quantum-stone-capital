"""
End-to-end ML pipeline: features -> train -> walk-forward -> predict.
"""
from typing import List
import numpy as np

from ml.features.feature_builder import FeatureBuilder
from ml.models.base import BaseModel
from ml.models.boosted import XGBoostModel, LightGBMModel
from ml.models.ppo_agent import PPOAgent
from ml.backtest.walk_forward import walk_forward_splits
from ml.backtest.metrics import sharpe_ratio, max_drawdown, deflated_sharpe_ratio


class MLPipeline:
    """Train, evaluate, and predict with any BaseModel."""

    MODEL_REGISTRY = {
        "xgboost": XGBoostModel,
        "lightgbm": LightGBMModel,
        "ppo": PPOAgent,
    }

    def __init__(self, model_type: str = "xgboost", **model_kwargs):
        if model_type not in self.MODEL_REGISTRY:
            raise ValueError("Unknown model: " + model_type)
        self.model_type = model_type
        self.model: BaseModel = self.MODEL_REGISTRY[model_type](**model_kwargs)

    @staticmethod
    def build_features(closes: List[float], highs: List[float], lows: List[float]) -> np.ndarray:
        X = []
        for i in range(60, len(closes) + 1):
            X.append(FeatureBuilder.build(closes[:i], highs[:i], lows[:i]))
        return np.array(X, dtype=float)

    @staticmethod
    def build_labels(closes: List[float], horizon: int = 1) -> np.ndarray:
        labels = []
        for i in range(60, len(closes)):
            if i + horizon - 1 < len(closes):
                fwd = closes[i + horizon - 1] / closes[i - 1] - 1.0
                labels.append(1 if fwd > 0 else 0)
        return np.array(labels, dtype=int)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MLPipeline":
        if X.shape[0] != y.shape[0]:
            raise ValueError("X and y length mismatch")
        self.model.fit(X, y)
        return self

    def walk_forward_evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_size: int = 200,
        test_size: int = 50,
        purge: int = 5,
        embargo: int = 5,
    ) -> dict:
        sharpes = []
        dds = []
        for split in walk_forward_splits(
            len(X), train_size, test_size, purge=purge, embargo=embargo,
        ):
            Xtr = X[split.train_idx]
            ytr = y[split.train_idx]
            Xte = X[split.test_idx]
            yte = y[split.test_idx]
            model = self.MODEL_REGISTRY[self.model_type]()
            model.fit(Xtr, ytr)
            probs = model.predict_proba(Xte)
            preds = (probs >= 0.5).astype(int)
            rets = (preds * 2 - 1) * (yte - 0.5)
            sharpes.append(sharpe_ratio(list(rets)))
            eq = np.cumprod(1 + np.array(rets) * 0.01)
            dds.append(max_drawdown(list(eq)))
        mean_sharpe = float(np.mean(sharpes)) if sharpes else 0.0
        return {
            "n_splits": len(sharpes),
            "mean_sharpe": mean_sharpe,
            "max_dd_mean": float(np.mean(dds)) if dds else 0.0,
            "deflated_sharpe": deflated_sharpe_ratio(mean_sharpe, len(sharpes) or 1, len(X)),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)
