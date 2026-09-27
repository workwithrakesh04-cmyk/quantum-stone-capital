"""
Signal Filter.
Rejects middle signals, keeps only extreme realizations.
Implements the Brunnermeier principle: only act on extremes.
"""
from typing import List, Optional


class SignalFilter:
    """
    Extreme-only filter.
    z = (signal - mean) / std
    If |z| < min_z_score: return 0.0 (no trade)
    Else: scale |z| / scale_max clipped to [0, 1]
    """

    def __init__(self, min_z_score: float = 1.5, scale_max: float = 3.0):
        self.min_z_score = min_z_score
        self.scale_max = scale_max

    def z_score(self, value: float, mean: float, std: float) -> float:
        if std == 0:
            return 0.0
        return (value - mean) / std

    def score(
        self,
        signal_value: float,
        signal_history: List[float],
    ) -> float:
        """Return a [0, 1] confidence score. 0 = no trade."""
        if len(signal_history) < 2:
            return 0.0
        mean = sum(signal_history) / len(signal_history)
        var = sum((x - mean) ** 2 for x in signal_history) / (len(signal_history) - 1)
        std = var ** 0.5
        z = self.z_score(signal_value, mean, std)
        if abs(z) < self.min_z_score:
            return 0.0
        return min(abs(z) / self.scale_max, 1.0)

    def passes(
        self,
        signal_value: float,
        signal_history: List[float],
    ) -> bool:
        return self.score(signal_value, signal_history) > 0.0
