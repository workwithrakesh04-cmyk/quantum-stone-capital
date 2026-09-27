"""Fibonacci helpers: retracements, extensions, and ratio sets."""
from typing import List


RETRACEMENT_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
EXTENSION_RATIOS = [1.0, 1.272, 1.618, 2.618, 4.236]


def retracement_levels(start: float, end: float, ratios: List[float] = None) -> dict:
    """Return {ratio: price} for retracements of an impulse (start -> end)."""
    ratios = ratios or RETRACEMENT_RATIOS
    return {r: end - (end - start) * r for r in ratios}


def extension_levels(start: float, end: float, ratios: List[float] = None) -> dict:
    """Return {ratio: price} for extension targets beyond end."""
    ratios = ratios or EXTENSION_RATIOS
    return {r: start + (end - start) * r for r in ratios}


def nearest_ratio(value: float, ratios: List[float], tolerance: float = 0.02) -> float:
    """Return the closest ratio within tolerance, or 0.0 if none."""
    if not ratios:
        return 0.0
    closest = min(ratios, key=lambda r: abs(value - r))
    if abs(value - closest) <= tolerance:
        return closest
    return 0.0
