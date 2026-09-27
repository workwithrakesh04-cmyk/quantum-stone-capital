"""
Debate Engine: orchestrates the workers and jurors.
1. Runs Bull/Bear/Hold to generate arguments.
2. Weighs arguments to produce a trade proposal (direction + confidence).
3. Runs the three jurors (Risk, Strategy, Execution).
4. Returns a final decision.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from workers.bull_bot import BullBot
from workers.bear_bot import BearBot
from workers.hold_bot import HoldBot
from workers.base_worker import Argument
from jurors.risk_juror import RiskJuror
from jurors.strategy_juror import StrategyJuror
from jurors.execution_juror import ExecutionJuror
from jurors.base_juror import Verdict


@dataclass
class DebateResult:
    direction: str
    confidence: float
    arguments: List[Argument] = field(default_factory=list)
    verdicts: List[Verdict] = field(default_factory=list)
    decision: str = "no_trade"
    reasons: List[str] = field(default_factory=list)


class DebateEngine:
    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.bull = BullBot()
        self.bear = BearBot()
        self.hold = HoldBot()
        self.risk_juror = RiskJuror(**config.get("risk", {}))
        self.strategy_juror = StrategyJuror(**config.get("strategy", {}))
        self.execution_juror = ExecutionJuror(**config.get("execution", {}))

    def debate(self, context: dict, proposal: Optional[dict] = None) -> DebateResult:
        args = [
            self.bull.analyze(context),
            self.bear.analyze(context),
            self.hold.analyze(context),
        ]

        direction, confidence = self._aggregate(args)

        verdicts = []
        if direction != "flat" and proposal is not None:
            proposal = dict(proposal)
            proposal.setdefault("direction", direction)
            verdicts = [
                self.risk_juror.judge(proposal),
                self.strategy_juror.judge(proposal),
                self.execution_juror.judge(proposal),
            ]

        if direction == "flat":
            return DebateResult(
                direction=direction, confidence=confidence,
                arguments=args, verdicts=verdicts,
                decision="no_trade",
                reasons=["no_directional_conviction"],
            )

        if any(not v.approved for v in verdicts):
            reasons = [v.reason for v in verdicts if not v.approved]
            return DebateResult(
                direction=direction, confidence=confidence,
                arguments=args, verdicts=verdicts,
                decision="no_trade",
                reasons=reasons,
            )

        return DebateResult(
            direction=direction, confidence=confidence,
            arguments=args, verdicts=verdicts,
            decision="trade",
            reasons=["all_jurors_approved"],
        )

    def _aggregate(self, args: List[Argument]) -> tuple:
        long_score = 0.0
        short_score = 0.0
        hold_score = 0.0
        for a in args:
            if a.direction == "long":
                long_score += a.confidence
            elif a.direction == "short":
                short_score += a.confidence
            elif a.direction == "flat":
                hold_score += a.confidence

        if long_score > short_score and long_score > hold_score:
            direction = "long"
            confidence = long_score - short_score * 0.5
        elif short_score > long_score and short_score > hold_score:
            direction = "short"
            confidence = short_score - long_score * 0.5
        else:
            direction = "flat"
            confidence = hold_score

        confidence = max(0.0, min(1.0, confidence))
        if confidence < 0.3:
            direction = "flat"
        return direction, confidence
