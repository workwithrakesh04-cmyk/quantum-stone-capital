"""
Bull worker: looks for reasons to go long.
Weighs bullish evidence from microstructure, momentum, structure, and order flow.
"""
from workers.base_worker import BaseWorker, Argument


class BullBot(BaseWorker):
    name = "bull"

    def analyze(self, context: dict) -> Argument:
        evidence = []
        score = 0.0
        n_signals = 0

        # Momentum
        momentum = context.get("momentum")
        if momentum is not None:
            n_signals += 1
            if momentum > 0.02:
                score += 1.0
                evidence.append("positive_momentum")
            elif momentum > 0:
                score += 0.3
                evidence.append("mild_positive_momentum")

        # RSI extremes (oversold rebound)
        rsi = context.get("rsi")
        if rsi is not None:
            n_signals += 1
            if rsi < 30:
                score += 1.0
                evidence.append("rsi_oversold")
            elif rsi < 45:
                score += 0.3
                evidence.append("rsi_approaching_oversold")

        # Structure (BOS bullish)
        bos = context.get("bos")
        if bos is not None:
            n_signals += 1
            if bos == "BOS_BULLISH":
                score += 1.0
                evidence.append("bullish_bos")
            elif bos == "CHOCH_BULLISH":
                score += 0.7
                evidence.append("bullish_choch")

        # Order flow (positive delta)
        delta = context.get("delta")
        if delta is not None:
            n_signals += 1
            if delta > 0:
                score += 0.5
                evidence.append("positive_delta")

        # Regime
        regime = context.get("regime")
        if regime == "trending_up":
            score += 0.5
            evidence.append("uptrend_regime")

        # Harmonic / EW
        if context.get("harmonic_bullish"):
            score += 0.7
            evidence.append("bullish_harmonic")
        if context.get("wave3_active"):
            score += 0.8
            evidence.append("wave3_active")

        # Signal filter
        if context.get("passes_filter"):
            score += 0.4
            evidence.append("passes_extreme_filter")

        max_score = max(n_signals, 1) + 3.0
        confidence = min(score / max_score, 1.0)

        direction = "long" if confidence >= 0.3 else "flat"
        return Argument(
            worker=self.name,
            direction=direction,
            confidence=confidence,
            evidence=evidence,
            rationale="Bullish evidence: " + ", ".join(evidence) if evidence else "No bullish evidence",
        )
