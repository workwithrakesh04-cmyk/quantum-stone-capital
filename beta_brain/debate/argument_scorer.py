"""Argument Scorer - evaluates the quality of each bot's argument.

Score = confidence * evidence_quality_bonus
evidence_quality_bonus = 1.0 + min(evidence_count / 10, 0.3)
"""
from typing import List
from beta_brain.debate.transcript import Argument


class ArgumentScorer:
    def score(self, arg: Argument) -> float:
        conf = arg.confidence
        evidence_count = len(arg.evidence) if arg.evidence else 0
        bonus = 1.0 + min(evidence_count / 10.0, 0.3)
        return round(conf * bonus, 3)

    def rank(self, args: List[Argument]) -> List[Argument]:
        return sorted(args, key=lambda a: self.score(a), reverse=True)

    def best(self, args: List[Argument]) -> Argument:
        if not args:
            raise ValueError("No arguments to score")
        return max(args, key=lambda a: self.score(a))
