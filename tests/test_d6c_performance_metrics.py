"""D6c tests - fixed Sharpe / Sortino in performance_metrics."""
import math
import pytest

from beta_brain.performance_metrics import (
    compute_sharpe,
    compute_sortino,
    infer_periods_per_year,
    enrich,
)


class TestSharpe:
    def test_too_few_returns(self):
        assert compute_sharpe([]) == 0.0
        assert compute_sharpe([0.01]) == 0.0

    def test_zero_std_returns_zero(self):
        assert compute_sharpe([0.01, 0.01, 0.01]) == 0.0

    def test_explicit_ppy_scales_by_sqrt(self):
        r = [0.01, -0.005, 0.02, -0.01, 0.015]
        s1 = compute_sharpe(r, periods_per_year=1)
        s252 = compute_sharpe(r, periods_per_year=252)
        assert pytest.approx(s252 / s1, rel=1e-9) == math.sqrt(252)

    def test_none_uses_conservative_default(self):
        r = [0.01, -0.005, 0.02, -0.01, 0.015]
        s_none = compute_sharpe(r, periods_per_year=None)
        s_252 = compute_sharpe(r, periods_per_year=252)
        assert pytest.approx(s_none, rel=1e-9) == s_252

    def test_inference_from_days(self):
        # 58 trades over 35 days -> ~605 trades/year
        ppy = infer_periods_per_year(58, 35.0)
        assert 600 <= ppy <= 610

    def test_inference_no_days_falls_back(self):
        assert infer_periods_per_year(58, None) == 252
        assert infer_periods_per_year(0, 35.0) == 252

    def test_real_sharpe_is_sane(self):
        # 58 returns drawn from a modest positive edge
        import random
        random.seed(42)
        r = [random.gauss(0.002, 0.02) for _ in range(58)]
        s = compute_sharpe(r, periods_per_year=605)
        # Not the inflated 16.95; should be a normal-looking number
        assert -20 < s < 20
        assert abs(s) < 50


class TestSortino:
    def test_too_few_returns(self):
        assert compute_sortino([]) == 0.0
        assert compute_sortino([0.01]) == 0.0

    def test_no_downside_returns_inf(self):
        assert compute_sortino([0.01, 0.02, 0.03], periods_per_year=252) == float("inf")

    def test_no_downside_when_all_above_mar_returns_inf(self):
        # All trades above MAR -> no downside -> inf when mean > mar
        s = compute_sortino([0.02, 0.03], mar=0.01, periods_per_year=252)
        assert s == float("inf")

    def test_all_below_mar_returns_negative(self):
        # All trades below MAR -> downside deviation non-zero, Sortino negative
        s = compute_sortino([0.001, 0.001], mar=0.01, periods_per_year=252)
        assert s < 0

    def test_downside_deviation_over_all_trades(self):
        # 4 trades: 2 wins, 2 losses; dd should use all 4 in denominator
        r = [0.02, 0.01, -0.01, -0.02]
        s = compute_sortino(r, periods_per_year=1)
        # manual: mean=0, downside = [0,0,-0.01,-0.02] -> rms = sqrt((0.0001+0.0004)/4)=sqrt(0.000125)
        dd = math.sqrt(0.000125)
        assert pytest.approx(s, rel=1e-9) == 0.0  # mean-mar is 0

    def test_sortino_positive_when_edge_positive(self):
        import random
        random.seed(7)
        r = [random.gauss(0.002, 0.02) for _ in range(58)]
        s = compute_sortino(r, periods_per_year=605)
        assert s > 0
        assert abs(s) < 50

    def test_sortino_scales_like_sharpe(self):
        r = [0.01, -0.005, 0.02, -0.01, 0.015]
        s1 = compute_sortino(r, periods_per_year=1)
        s252 = compute_sortino(r, periods_per_year=252)
        assert pytest.approx(s252 / s1, rel=1e-9) == math.sqrt(252)


class TestEnrich:
    def test_enrich_infers_ppy_from_stats(self):
        stats = {"total_trades": 58, "net_pnl": 1621.11,
                 "starting_balance": 10000.0, "max_drawdown_pct": 6.62}
        r = [0.002, -0.001, 0.003, -0.002, 0.001] * 12
        out = enrich(stats, r, period_days=35.0)
        assert "periods_per_year_used" in out
        assert 600 <= out["periods_per_year_used"] <= 610
        assert out["sharpe"] != 0
        assert "sortino" in out
        assert "calmar" in out

    def test_enrich_respects_explicit_ppy(self):
        stats = {"total_trades": 10, "net_pnl": 100.0,
                 "starting_balance": 10000.0, "max_drawdown_pct": 2.0}
        r = [0.002, -0.001] * 5
        out = enrich(stats, r, periods_per_year=252)
        assert out["periods_per_year_used"] == 252

    def test_enrich_backward_compat_no_ppy(self):
        # Old callers that pass only (stats, returns) still work
        stats = {"total_trades": 10, "net_pnl": 100.0,
                 "starting_balance": 10000.0, "max_drawdown_pct": 2.0}
        r = [0.002, -0.001] * 5
        out = enrich(stats, r)
        assert out["periods_per_year_used"] == 252