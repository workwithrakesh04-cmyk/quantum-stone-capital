"""
Bear worker: looks for reasons to go short.
Mirror of BullBot with bearish evidence.
"""
from workers.base_worker import BaseWorker, Argument


class BearBot(BaseWorker):
    name = "bear"

    def analyze(self, context: dict) -> Argument:
        evidence = []
        score = 0.0
        n_signals = 0

        momentum = context.get("momentum")
        if momentum is not None:
            n_signals += 1
            if momentum < -0.02:
                score += 1.0
                evidence.append("negative_momentum")
            elif momentum < 0:
                score += 0.3
                evidence.append("mild_negative_momentum")

        rsi = context.get("rsi")
        if rsi is not None:
            n_signals += 1
            if rsi > 70:
                score += 1.0
                evidence.append("rsi_overbought")
            elif rsi > 55:
                score += 0.3
                evidence.append("rsi_approaching_overbought")

        bos = context.get("bos")
        if bos is not None:
            n_signals += 1
            if bos == "BOS_BEARISH":
                score += 1.0
                evidence.append("bearish_bos")
            elif bos == "CHOCH_BEARISH":
                score += 0.7
                evidence.append("bearish_choch")

        delta = context.get("delta")
        if delta is not None:
            n_signals += 1
            if delta < 0:
                score += 0.5
                evidence.append("negative_delta")

        regime = context.get("regime")
        if regime == "trending_down":
            score += 0.5
            evidence.append("downtrend_regime")

        if context.get("harmonic_bearish"):
            score += 0.7
            evidence.append("bearish_harmonic")
        if context.get("wave_c_active"):
            score += 0.8
            evidence.append("wave_c_active")

        if context.get("passes_filter"):
            score += 0.4
            evidence.append("passes_extreme_filter")

        max_score = max(n_signals, 1) + 3.0
        confidence = min(score / max_score, 1.0)

        direction = "short" if confidence >= 0.3 else "flat"
        return Argument(
            worker=self.name,
            direction=direction,
            confidence=confidence,
            evidence=evidence,
            rationale="Bearish evidence: " + ", ".join(evidence) if evidence else "No bearish evidence",
        )
