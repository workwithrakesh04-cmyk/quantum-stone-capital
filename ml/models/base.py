"""Base model interface for all ML models in the pipeline."""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseModel(ABC):
    """Every ML model in the pipeline implements this interface."""

    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseModel":
        """Train the model."""

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return class predictions (0/1)."""

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability of class 1."""

    @abstractmethod
    def save(self, path: str) -> None:
        """Persist model to disk."""

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> "BaseModel":
        """Load model from disk."""
