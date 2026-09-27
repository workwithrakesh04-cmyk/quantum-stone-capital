"""Bayesian Fair Value - Glosten-Milgrom framework."""


def bayesian_update(prior: float, likelihood_h: float, likelihood_not_h: float) -> float:
    evidence = likelihood_h * prior + likelihood_not_h * (1 - prior)
    if evidence == 0:
        return prior
    return (likelihood_h * prior) / evidence
