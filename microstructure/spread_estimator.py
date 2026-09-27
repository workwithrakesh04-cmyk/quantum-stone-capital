"""Spread estimator - adverse selection + competition."""


def estimate_spread(volatility, informed_ratio, competition_level) -> float:
    base_spread = volatility * 0.5
    adverse_selection = informed_ratio * 2
    competition_compression = 1.0 / (1 + competition_level)
    return base_spread * (1 + adverse_selection) * competition_compression
