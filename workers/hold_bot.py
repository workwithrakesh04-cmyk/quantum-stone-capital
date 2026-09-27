"""
Hold worker: argues for staying flat (no trade).
Fires when evidence is conflicting, weak, or when risk conditions are poor.
"""
from workers.base_worker import BaseWorker, Argument


class HoldBot(BaseWorker):
    name = "hold"

    def analyze(self, context: dict) -> Argument:
        evidence = []
        score = 0.0

        # Conflicting signals strengthen the hold case
        bull_evidence = context.get("bull_evidence_count", 0)
        bear_evidence = context.get("bear_evidence_count", 0)

        if bull_evidence > 0 and bear_evidence > 0:
            score += 0.5
            evidence.append("conflicting_signals")

        # Middle signals (no extreme)
        if not context.get("passes_filter", False):
            score += 0.3
            evidence.append("signal_not_extreme")

        # Ranging market — mean reversion less reliable
        if context.get("regime") == "ranging":
            score += 0.2
            evidence.append("ranging_market")

        # High volatility — avoid
        volatility = context.get("volatility")
        if volatility is not None and volatility > 0.05:
            score += 0.4
            evidence.append("high_volatility")

        # Session-based: off hours
        session = context.get("session")
        if session == "off_hours":
            score += 0.3
            evidence.append("off_hours_session")

        # Weekend
        if context.get("is_weekend", False):
            score += 0.5
            evidence.append("weekend")

        # Low liquidity
        if context.get("is_illiquid", False):
            score += 0.4
            evidence.append("illiquid_market")

        confidence = min(score, 1.0)
        direction = "flat" if confidence >= 0.3 else "flat"  # Hold always favors flat

        return Argument(
            worker=self.name,
            direction=direction,
            confidence=confidence,
            evidence=evidence,
            rationale="Hold rationale: " + ", ".join(evidence) if evidence else "No reason to hold",
        )
