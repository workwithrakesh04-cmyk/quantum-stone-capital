"""Tests for MicrostructureEngine."""
import math
import pytest
from microstructure.engine import MicrostructureEngine, MicrostructureState


@pytest.fixture
def engine():
    return MicrostructureEngine(sigma_u=1.0, competition_level=0.5)


def test_kyle_lambda_basic(engine):
    lam = engine.kyle_lambda(sigma_0=1.0)
    # lambda = 0.5 * sqrt(1 / 1) = 0.5
    assert abs(lam - 0.5) < 1e-9


def test_kyle_lambda_zero_sigma_u():
    eng = MicrostructureEngine(sigma_u=0.0)
    assert eng.kyle_lambda(sigma_0=1.0) == float("inf")


def test_kyle_lambda_increases_with_info(engine):
    lam_low = engine.kyle_lambda(sigma_0=0.1)
    lam_high = engine.kyle_lambda(sigma_0=10.0)
    assert lam_high > lam_low


def test_bayesian_fair_value_zero_flow(engine):
    fv = engine.bayesian_fair_value(order_flow=0.0, prior_mean=100.0, prior_var=1.0)
    assert fv == 100.0


def test_bayesian_fair_value_positive_flow(engine):
    fv = engine.bayesian_fair_value(order_flow=2.0, prior_mean=100.0, prior_var=1.0)
    assert fv > 100.0


def test_bayesian_fair_value_negative_flow(engine):
    fv = engine.bayesian_fair_value(order_flow=-2.0, prior_mean=100.0, prior_var=1.0)
    assert fv < 100.0


def test_estimate_spread_positive(engine):
    spread = engine.estimate_spread(volatility=1.0, informed_ratio=0.1)
    assert spread > 0


def test_estimate_spread_widens_with_info(engine):
    s_low = engine.estimate_spread(volatility=1.0, informed_ratio=0.05)
    s_high = engine.estimate_spread(volatility=1.0, informed_ratio=0.5)
    assert s_high > s_low


def test_snapshot_shape(engine):
    state = engine.snapshot(
        sigma_0=1.0, order_flow=0.5, prior_mean=100.0,
        prior_var=1.0, volatility=1.0, informed_ratio=0.1,
    )
    assert isinstance(state, MicrostructureState)
    assert state.kyle_lambda > 0
    assert state.spread_estimate > 0
    assert isinstance(state.is_illiquid, bool)


def test_suggest_execution_small_order(engine):
    rec = engine.suggest_execution(order_size=1.0, avg_volume=100000.0, sigma_0=0.01)
    assert rec["recommendation"] in ("MARKET_ORDER", "TWAP")
    assert rec["child_order_count"] >= 1


def test_suggest_execution_large_order_splits(engine):
    rec = engine.suggest_execution(order_size=100000.0, avg_volume=100.0, sigma_0=10.0)
    assert rec["recommendation"] == "TWAP"
    assert rec["child_order_count"] >= 2
