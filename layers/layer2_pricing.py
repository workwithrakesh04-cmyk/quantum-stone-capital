"""Layer 2 — Pricing. Wraps PricingEngine as a layer."""
from core.pricing_engine import PricingEngine


class Layer2Pricing:
    def __init__(self):
        self.engine = PricingEngine()

    def forward(self, *args, **kwargs):
        return self.engine.forward_price(*args, **kwargs)

    def parity_check(self, *args, **kwargs):
        return self.engine.put_call_parity_check(*args, **kwargs)

    def kyle_lambda(self, sigma_0: float, sigma_u: float) -> float:
        return self.engine.kyle_lambda(sigma_0, sigma_u)
