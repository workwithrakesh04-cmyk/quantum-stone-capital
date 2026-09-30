"""HOLD BOT - argues for WAIT based on signal conflict / low conviction."""
from typing import List, Dict, Any

from beta_brain.signal import Signal
from beta_brain.debate.transcript import Argument


class HoldBot:
    NAME = "HOLD"

    def __init__(self):
        self.confidence = 0.0
        self.evidence: List[Dict[str, Any]] = []
        self.statement = ""

    def argue(self, signals: List[Signal], market_context: Dict[str, Any]) -> Argument:
        long_count = sum(1 for s in signals if s.direction == "LONG")
        short_count = sum(1 for s in signals if s.direction == "SHORT")
        total_actionable = long_count + short_count

        conflict_score = 0.0
        if long_count > 0 and short_count > 0:
            ratio = min(long_count, short_count) / max(long_count, short_count)
            conflict_score = 0.4 * ratio

        long_conf = sum(s.confidence for s in signals if s.direction == "LONG")
        short_conf = sum(s.confidence for s in signals if s.direction == "SHORT")
        total_conviction = long_conf + short_conf
        low_conviction_score = max(0.0, 0.3 - total_conviction * 0.1)

        volatility_score = 0.0
        vol = market_context.get("volatility", 0.0)
        if vol < 0.3:
            volatility_score = (0.3 - vol) * 0.5

        evidence = [
            {"type": "signal_conflict", "long": long_count, "short": short_count, "score": conflict_score},
            {"type": "low_conviction", "total": total_conviction, "score": low_conviction_score},
            {"type": "volatility", "value": vol, "score": volatility_score},
        ]

        raw = conflict_score + low_conviction_score + volatility_score + 0.15
        confidence = max(0.0, min(raw, 1.0))

        self.confidence = confidence
        self.evidence = evidence

        if total_actionable == 0:
            self.statement = "No actionable signals. WAIT confirmed."
        else:
            self.statement = (
                f"Conflict={conflict_score:.2f}, Low-conviction={low_conviction_score:.2f}, "
                f"Vol-score={volatility_score:.2f}"
            )

        return Argument(
            bot=self.NAME, round=1,
            confidence=round(confidence, 3),
            statement=self.statement, evidence=evidence,
        )

    def rebut(self, my_arg: Argument, opp_arg: Argument) -> Argument:
        rebuttals = []
        opp_conf = opp_arg.confidence
        if opp_conf < 0.5:
            rebuttals.append(f"{opp_arg.bot} only has {opp_conf:.2f}")
        if opp_conf >= 0.5:
            rebuttals.append(f"{opp_arg.bot} at {opp_conf:.2f} - conflict remains")

        self.statement = " | ".join(rebuttals) if rebuttals else "HOLD safest"
        return Argument(
            bot=self.NAME, round=2,
            confidence=round(self.confidence, 3),
            statement=self.statement,
            evidence=self.evidence, rebuttals=rebuttals,
        )

    def close(self, round2_arg: Argument, market_context: Dict[str, Any]) -> Argument:
        return Argument(
            bot=self.NAME, round=3,
            confidence=round(self.confidence, 3),
            statement=f"HOLD stands at {self.confidence:.2f}",
            evidence=self.evidence,
        )

    def get_confidence(self) -> float:
        return self.confidence
