"""Kyle's Lambda - market illiquidity measure."""
import math


def kyle_lambda(sigma_0: float, sigma_u: float) -> float:
    if sigma_u <= 0:
        return float("inf")
    return 0.5 * math.sqrt(sigma_0 / sigma_u)
