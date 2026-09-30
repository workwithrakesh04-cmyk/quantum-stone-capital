"""BUY BOT - argues for LONG position based on Beta signals."""
from typing import List, Dict, Any

from beta_brain.signal import Signal
from beta_brain.debate.transcript import Argument


class BuyBot:
    NAME = "BUY"

    def __init__(self):
        self.confidence = 0.0
        self.evidence: List[Dict[str, Any]] = []
        self.statement = ""

    def argue(self, signals: List[Signal], market_context: Dict[str, Any]) -> Argument:
        long_signals = [s for s in signals if s.direction == "LONG"]
        short_signals = [s for s in signals if s.direction == "SHORT"]

        buy_score = 0.0
        evidence = []

        for s in long_signals:
            contribution = s.confidence * s.weight
            buy_score += contribution
            evidence.append({
                "strategy": s.strategy,
                "confidence": s.confidence,
                "weight": s.weight,
                "reason": s.reason,
            })

        sell_counter = sum(s.confidence * s.weight for s in short_signals)

        momentum_bonus = 0.0
        if "momentum" in market_context:
            mom = market_context["momentum"]
            if mom > 0:
                momentum_bonus = min(mom * 0.15, 0.15)

        raw = buy_score - (sell_counter * 0.3) + momentum_bonus
        confidence = max(0.0, min(raw / 2.0, 1.0))

        self.confidence = confidence
        self.evidence = evidence

        if not long_signals:
            self.statement = f"No LONG signals. {len(short_signals)} SHORT seen."
        else:
            self.statement = (
                f"{len(long_signals)} LONG signals (top: {long_signals[0].strategy}). "
                f"Counter: {len(short_signals)} SHORT. "
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
            rebuttals.append(f"SELL weak (conf={opp_conf:.2f})")
        opp_strategies = [e.get("strategy", "") for e in opp_arg.evidence if isinstance(e, dict)]
        if opp_strategies:
            rebuttals.append(f"SELL relies on {opp_strategies[0]}")
        if self.confidence > opp_conf:
            rebuttals.append(f"BUY higher conf ({self.confidence:.2f} vs {opp_conf:.2f})")

        self.statement = " | ".join(rebuttals) if rebuttals else "BUY case stands"
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
            statement=f"BUY stands at {self.confidence:.2f}",
            evidence=self.evidence,
        )

    def get_confidence(self) -> float:
        return self.confidence
