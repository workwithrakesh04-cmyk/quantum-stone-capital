"""Gradient-boosted tree models: XGBoost and LightGBM."""
from typing import Optional
import numpy as np

from ml.models.base import BaseModel


class XGBoostModel(BaseModel):
    name = "xgboost"

    def __init__(self, n_estimators: int = 200, max_depth: int = 4,
                 learning_rate: float = 0.05, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self._model = None

    def fit(self, X, y):
        from xgboost import XGBClassifier
        self._model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            use_label_encoder=False,
            eval_metric="logloss",
        )
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)[:, 1]

    def save(self, path):
        import joblib
        joblib.dump(self._model, path)

    @classmethod
    def load(cls, path):
        import joblib
        obj = cls()
        obj._model = joblib.load(path)
        return obj


class LightGBMModel(BaseModel):
    name = "lightgbm"

    def __init__(self, n_estimators: int = 200, max_depth: int = -1,
                 learning_rate: float = 0.05, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self._model = None

    def fit(self, X, y):
        from lightgbm import LGBMClassifier
        self._model = LGBMClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            verbose=-1,
        )
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)[:, 1]

    def save(self, path):
        import joblib
        joblib.dump(self._model, path)

    @classmethod
    def load(cls, path):
        import joblib
        obj = cls()
        obj._model = joblib.load(path)
        return obj
