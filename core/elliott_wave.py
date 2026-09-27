"""
Elliott Wave Engine (Frost & Prechter).
Validates 5-wave impulses against Elliott's hard rules,
computes Fibonacci targets, and returns invalidation levels.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WavePoint:
    price: float
    index: int


class ElliottWaveEngine:
    """
    Validates a 5-wave impulse given points for waves 0..5.
    """

    def validate_impulse(self, waves: Dict[int, WavePoint]) -> dict:
        violations = []
        try:
            w0 = waves[0].price
            w1 = waves[1].price
            w2 = waves[2].price
            w3 = waves[3].price
            w4 = waves[4].price
            w5 = waves[5].price
        except KeyError:
            return {"valid": False, "violations": ["missing waves"]}

        # Rule 1: wave 2 never retraces > 100% of wave 1
        if w2 <= w0:
            violations.append("Rule 1: wave 2 > 100% retrace")

        # Rule 4: wave 3 always exceeds wave 1
        if w3 <= w1:
            violations.append("Rule 4: wave 3 must exceed wave 1")

        # Rule 2: wave 3 never the shortest actionary wave
        w1_len = abs(w1 - w0)
        w3_len = abs(w3 - w2)
        w5_len = abs(w5 - w4)
        if w3_len < w1_len and w3_len < w5_len:
            violations.append("Rule 2: wave 3 shortest")

        # Rule 3: wave 4 no overlap with wave 1 territory
        if w4 <= w1:
            violations.append("Rule 3: wave 4 overlaps wave 1")

        # Rule 6: wave 4 retrace of wave 3 not > 100%
        if w4 <= w2:
            violations.append("Rule 6: wave 4 retraced > 100% of wave 3")

        return {"valid": len(violations) == 0, "violations": violations}

    def wave3_targets(self, w1_start: float, w1_end: float, w2_end: float) -> dict:
        w1_len = abs(w1_end - w1_start)
        return {
            "0.618": w2_end + 0.618 * w1_len,
            "1.000": w2_end + 1.000 * w1_len,
            "1.618": w2_end + 1.618 * w1_len,
            "2.618": w2_end + 2.618 * w1_len,
        }

    def wave5_targets(self, w4_end: float, w3_len: float) -> dict:
        return {
            "0.382": w4_end + 0.382 * w3_len,
            "0.618": w4_end + 0.618 * w3_len,
            "1.000": w4_end + 1.000 * w3_len,
            "1.618": w4_end + 1.618 * w3_len,
        }

    def invalidation_level(self, waves: Dict[int, WavePoint]) -> float:
        if 4 in waves and 2 in waves:
            return waves[2].price
        if 3 in waves and 1 in waves:
            return waves[1].price
        if 2 in waves and 0 in waves:
            return waves[0].price
        return 0.0
