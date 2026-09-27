"""Pricing Engine - Layer 2. FRM formulas: forwards, put-call parity, convenience yield."""
import math


class PricingEngine:
    """FRM Chapters 10, 11, 13 integration."""

    @staticmethod
    def forward_price(
        spot: float,
        risk_free_rate: float,
        time_to_maturity: float,
        income_pv: float = 0.0,
        yield_rate: float = 0.0,
        storage_cost: float = 0.0,
        convenience_yield: float = 0.0,
        continuous: bool = True,
    ) -> float:
        if continuous:
            carry = risk_free_rate + storage_cost - convenience_yield
            return spot * math.exp(carry * time_to_maturity)
        if yield_rate > 0:
            return spot * ((1 + risk_free_rate) / (1 + yield_rate)) ** time_to_maturity
        if income_pv > 0:
            return (spot - income_pv) * (1 + risk_free_rate) ** time_to_maturity
        return spot * (1 + risk_free_rate) ** time_to_maturity

    @staticmethod
    def forward_value(current_forward, delivery_price, risk_free_rate, time_to_maturity) -> float:
        return (current_forward - delivery_price) / (1 + risk_free_rate) ** time_to_maturity

    @staticmethod
    def put_call_parity_check(
        call_price, put_price, spot, strike,
        risk_free_rate, time_to_maturity, tolerance: float = 0.01,
    ) -> dict:
        pv_k = strike / (1 + risk_free_rate) ** time_to_maturity
        lhs = call_price + pv_k
        rhs = put_price + spot
        diff = lhs - rhs
        return {
            "lhs": lhs, "rhs": rhs, "diff": diff,
            "arbitrage": abs(diff) > tolerance,
            "action": (
                "short_call_buy_put_buy_stock" if diff > tolerance
                else "long_call_sell_put_sell_stock" if diff < -tolerance
                else "none"
            ),
            "expected_profit": abs(diff),
        }

    @staticmethod
    def convenience_yield(spot, futures, risk_free_rate, storage_cost, time_to_maturity) -> float:
        if time_to_maturity <= 0 or spot <= 0 or futures <= 0:
            return 0.0
        implied_carry = math.log(futures / spot) / time_to_maturity
        return risk_free_rate + storage_cost - implied_carry

    @staticmethod
    def optimal_hedge_ratio(correlation, sigma_spot, sigma_futures) -> float:
        if sigma_futures == 0:
            return 0.0
        return correlation * (sigma_spot / sigma_futures)

    @staticmethod
    def kyle_lambda(sigma_0: float, sigma_u: float) -> float:
        if sigma_u <= 0:
            return float("inf")
        return 0.5 * math.sqrt(sigma_0 / sigma_u)
