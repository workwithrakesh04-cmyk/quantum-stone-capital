"""Tests for beta_brain.performance_metrics."""
from beta_brain.performance_metrics import (
    compute_sharpe, compute_sortino, expectancy, calmar_ratio, enrich,
)


def test_sharpe_insufficient_returns_zero():
    assert compute_sharpe([]) == 0.0
    assert compute_sharpe([0.01]) == 0.0


def test_sharpe_positive_returns():
    s = compute_sharpe([0.01, 0.02, 0.015, 0.005, 0.02])
    assert s > 0


def test_sharpe_zero_std_returns_zero():
    assert compute_sharpe([0.01, 0.01, 0.01]) == 0.0


def test_sortino_insufficient_returns_zero():
    assert compute_sortino([]) == 0.0


def test_sortino_no_downside_positive_mean():
    s = compute_sortino([0.01, 0.02, 0.03])
    assert s == float("inf")


def test_sortino_with_downside():
    s = compute_sortino([0.01, -0.005, 0.02, -0.01, 0.03])
    assert s > 0


def test_expectancy_zero_trades():
    assert expectancy({"total_trades": 0, "net_pnl": 100}) == 0.0


def test_expectancy_basic():
    assert expectancy({"total_trades": 10, "net_pnl": 100}) == 10.0


def test_calmar_zero_dd_returns_zero():
    assert calmar_ratio({"max_drawdown_pct": 0, "net_pnl": 100, "starting_balance": 1000}) == 0.0


def test_calmar_basic():
    r = calmar_ratio({"max_drawdown_pct": 5.0, "net_pnl": 100, "starting_balance": 1000})
    assert r == 2.0


def test_enrich_adds_fields():
    stats = {
        "total_trades": 5,
        "net_pnl": 50,
        "starting_balance": 10000,
        "max_drawdown_pct": 2.0,
    }
    out = enrich(stats, [0.01, 0.02, -0.005, 0.015, 0.01])
    assert "sharpe" in out
    assert "sortino" in out
    assert "expectancy_usd" in out
    assert "calmar" in out
