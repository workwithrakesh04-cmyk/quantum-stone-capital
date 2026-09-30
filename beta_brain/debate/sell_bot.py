"""SELL BOT - argues for SHORT position based on Beta signals."""
from typing import List, Dict, Any

from beta_brain.signal import Signal
from beta_brain.debate.transcript import Argument


class SellBot:
    NAME = "SELL"

    def __init__(self):
        self.confidence = 0.0
        self.evidence: List[Dict[str, Any]] = []
        self.statement = ""

    def argue(self, signals: List[Signal], market_context: Dict[str, Any]) -> Argument:
        short_signals = [s for s in signals if s.direction == "SHORT"]
        long_signals = [s for s in signals if s.direction == "LONG"]

        sell_score = 0.0
        evidence = []

        for s in short_signals:
            sell_score += s.confidence * s.weight
            evidence.append({
                "strategy": s.strategy,
                "confidence": s.confidence,
                "weight": s.weight,
                "reason": s.reason,
            })

        long_counter = sum(s.confidence * s.weight for s in long_signals)

        momentum_bonus = 0.0
        if "momentum" in market_context:
            mom = market_context["momentum"]
            if mom < 0:
                momentum_bonus = min(abs(mom) * 0.15, 0.15)

        raw = sell_score - (long_counter * 0.3) + momentum_bonus
        confidence = max(0.0, min(raw / 2.0, 1.0))

        self.confidence = confidence
        self.evidence = evidence

        if not short_signals:
            self.statement = f"No SHORT signals. {len(long_signals)} LONG seen."
        else:
            self.statement = (
                f"{len(short_signals)} SHORT signals (top: {short_signals[0].strategy}). "
                f"Counter: {len(long_signals)} LONG. "
                f"Momentum: {market_context.get('momentum', 0):.2f}"
            )

        return Argument(
            bot=self.NAME, round=1,
            confidence=round(confidence, 3),
            statement=self.statement, evidence=evidence,
        )

    def rebut(self, my_arg: Argument, opp_arg: Argument) -> Argument:
        rebuttals = []
        opp_conf = opp_arg.confidence
        if opp_conf < 0.4:
            rebuttals.append(f"BUY weak (conf={opp_conf:.2f})")
        opp_strategies = [e.get("strategy", "") for e in opp_arg.evidence if isinstance(e, dict)]
        if opp_strategies:
            rebuttals.append(f"BUY relies on {opp_strategies[0]}")
        if self.confidence > opp_conf:
            rebuttals.append(f"SELL higher conf ({self.confidence:.2f} vs {opp_conf:.2f})")

        self.statement = " | ".join(rebuttals) if rebuttals else "SELL case stands"
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
            statement=f"SELL stands at {self.confidence:.2f}",
            evidence=self.evidence,
        )

    def get_confidence(self) -> float:
        return self.confidence
