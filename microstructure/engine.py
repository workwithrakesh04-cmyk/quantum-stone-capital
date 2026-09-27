"""
Microstructure Engine.
Integrates Kyle's lambda, Bayesian fair value, and spread estimation
into a single class used by the Execution Juror and Algo Trader.
"""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class MicrostructureState:
    """Snapshot of current microstructure conditions."""
    kyle_lambda: float
    fair_value: float
    spread_estimate: float
    informed_ratio: float
    is_illiquid: bool


class MicrostructureEngine:
    """
    Combines:
      - Kyle (1985): market illiquidity measure
      - Glosten-Milgrom (1985): Bayesian fair value
      - Brunnermeier: spread estimation from adverse selection
    """

    def __init__(
        self,
        sigma_u: float = 1.0,
        competition_level: float = 0.5,
    ):
        self.sigma_u = sigma_u
        self.competition_level = competition_level

    def kyle_lambda(self, sigma_0: float) -> float:
        """lambda = 0.5 * sqrt(sigma_0 / sigma_u^2)"""
        if self.sigma_u <= 0:
            return float("inf")
        return 0.5 * math.sqrt(sigma_0 / (self.sigma_u ** 2))

    def bayesian_fair_value(
        self,
        order_flow: float,
        prior_mean: float,
        prior_var: float,
    ) -> float:
        """E[v | X] = prior + lambda * (X - E[X])"""
        lam = self.kyle_lambda(prior_var)
        return prior_mean + lam * order_flow

    def estimate_spread(
        self,
        volatility: float,
        informed_ratio: float,
    ) -> float:
        """Base spread scaled by adverse selection and competition."""
        base = volatility * 0.5
        adverse = informed_ratio * 2.0
        compression = 1.0 / (1.0 + self.competition_level)
        return base * (1.0 + adverse) * compression

    def snapshot(
        self,
        sigma_0: float,
        order_flow: float,
        prior_mean: float,
        prior_var: float,
        volatility: float,
        informed_ratio: float,
    ) -> MicrostructureState:
        """Return a full state snapshot for the decision layers."""
        lam = self.kyle_lambda(prior_var)
        fv = self.bayesian_fair_value(order_flow, prior_mean, prior_var)
        spr = self.estimate_spread(volatility, informed_ratio)
        return MicrostructureState(
            kyle_lambda=lam,
            fair_value=fv,
            spread_estimate=spr,
            informed_ratio=informed_ratio,
            is_illiquid=lam > 0.5,
        )

    def suggest_execution(
        self,
        order_size: float,
        avg_volume: float,
        sigma_0: float,
    ) -> dict:
        """
        Kyle-lambda-aware order splitting.
        If impact > 0.1%, recommend TWAP; else market order.
        """
        lam = self.kyle_lambda(sigma_0)
        impact = order_size * lam
        if impact > 0.001:
            child_count = max(2, int(order_size / max(avg_volume * 0.001, 1)))
            return {
                "recommendation": "TWAP",
                "child_order_count": child_count,
                "estimated_impact": impact,
            }
        return {
            "recommendation": "MARKET_ORDER",
            "child_order_count": 1,
            "estimated_impact": impact,
        }
