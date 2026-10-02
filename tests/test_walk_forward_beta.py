"""D8b tests - WalkForwardRunner window planning + aggregation."""
import pytest

from backtest.walk_forward_beta import (
    WalkForwardRunner,
    WalkForwardResult,
    WindowResult,
)


# ----------------------------------------------------------------------
# Window planning
# ----------------------------------------------------------------------

class TestPlanWindows:

    def _mk(self, **kw):
        defaults = dict(
            symbol="BTCUSDT", timeframe="5m",
            n_windows=10, window_size=3500, step_size=1500, warmup=100,
        )
        defaults.update(kw)
        return WalkForwardRunner(**defaults)

    def test_required_candles_formula(self):
        r = self._mk(n_windows=10, window_size=3500, step_size=1500, warmup=100)
        # 100 + 9*1500 + 3500 = 17100
        assert r.required_candles == 17100

    def test_raises_on_too_few(self):
        r = self._mk()
        with pytest.raises(ValueError):
            r.plan_windows(1000)

    def test_plan_count_and_bounds(self):
        r = self._mk()
        plans = r.plan_windows(20000)
        assert len(plans) == 10
        # first window starts at warmup
        assert plans[0]["window_start"] == 100
        assert plans[0]["window_end"] == 3600
        assert plans[0]["slice_start"] == 0
        # last window
        assert plans[-1]["window_start"] == 100 + 9 * 1500  # 13600
        assert plans[-1]["window_end"] == 13600 + 3500     # 17100
        assert plans[-1]["slice_start"] == 13600 - 100     # 13500

    def test_step_equals_window_no_overlap(self):
        r = self._mk(n_windows=4, window_size=1000, step_size=1000, warmup=50)
        plans = r.plan_windows(10000)
        assert len(plans) == 4
        # No overlap between window i and i+1
        for i in range(len(plans) - 1):
            assert plans[i]["window_end"] == plans[i + 1]["window_start"]

    def test_single_window(self):
        r = self._mk(n_windows=1, window_size=500, step_size=500, warmup=50)
        plans = r.plan_windows(2000)
        assert len(plans) == 1
        assert plans[0]["window_start"] == 50
        assert plans[0]["window_end"] == 550


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------

def _mk_window(idx, pnl, trades=None, sharpe=0.5, return_pct=1.0,
               dd_pct=2.0, regime="RANGING"):
    """Build a fake WindowResult."""
    trades = trades or []
    return WindowResult(
        index=idx,
        start_idx=0,
        end_idx=3500,
        start_iso="2026-01-01T00:00:00+00:00",
        end_iso="2026-01-02T00:00:00+00:00",
        n_candles=3500,
        runtime_sec=1.0,
        stats={
            "sharpe": sharpe,
            "sortino": sharpe * 1.2,
            "calmar": sharpe * 1.5,
            "return_pct": return_pct,
            "max_drawdown_pct": dd_pct,
            "total_trades": len(trades) or 1,
            "win_rate": 50.0,
            "profit_factor": 1.5,
            "net_pnl": pnl,
        },
        trades=trades,
        diagnostics={},
    )


class TestAggregation:

    def _runner(self):
        return WalkForwardRunner(
            n_windows=3, window_size=1000, step_size=500, warmup=50,
        )

    def test_empty(self):
        r = self._runner()
        assert r.aggregate([]) == {}

    def test_per_window_summary(self):
        r = self._runner()
        ws = [
            _mk_window(0, pnl=100, sharpe=1.0, return_pct=1.0),
            _mk_window(1, pnl=-50, sharpe=-0.5, return_pct=-0.5),
            _mk_window(2, pnl=200, sharpe=2.0, return_pct=2.0),
        ]
        agg = r.aggregate(ws)
        pws = agg["per_window_summary"]
        assert pws["n_windows"] == 3
        assert pws["sharpe_positive_windows"] == 2
        assert pws["return_pct_positive_windows"] == 2
        assert pws["sharpe_min"] == -0.5
        assert pws["sharpe_max"] == 2.0
        # mean of [1.0, -0.5, 2.0] = 0.8333...
        assert pytest.approx(pws["sharpe_mean"], abs=1e-3) == 0.8333
        # median = 1.0
        assert pws["sharpe_median"] == 1.0

    def test_chained_equity(self):
        r = self._runner()
        # 3 windows: +1%, +2%, -0.5%
        ws = [
            _mk_window(0, pnl=100, return_pct=1.0),
            _mk_window(1, pnl=200, return_pct=2.0),
            _mk_window(2, pnl=-50, return_pct=-0.5),
        ]
        agg = r.aggregate(ws)
        ch = agg["chained"]
        expected = 10000 * 1.01 * 1.02 * 0.995
        assert pytest.approx(ch["ending_balance"], abs=0.01) == expected
        assert ch["starting_balance"] == 10000.0
        assert len(ch["curve"]) == 4  # start + 3 windows

    def test_per_strategy_consistency(self):
        r = self._runner()
        # Strategy A: wins in windows 0 and 1, loses in 2
        # Strategy B: only in window 0, wins
        t_a_win = {"pnl_usd": 50.0, "contributing_strategies": ["A"], "regime": "RANGING"}
        t_a_lose = {"pnl_usd": -20.0, "contributing_strategies": ["A"], "regime": "RANGING"}
        t_b_win = {"pnl_usd": 100.0, "contributing_strategies": ["B"], "regime": "RANGING"}
        ws = [
            _mk_window(0, pnl=150, trades=[t_a_win, t_b_win]),
            _mk_window(1, pnl=50, trades=[t_a_win]),
            _mk_window(2, pnl=-20, trades=[t_a_lose]),
        ]
        agg = r.aggregate(ws)
        ps = agg["per_strategy"]
        assert ps["A"]["windows_present"] == 3
        assert ps["A"]["windows_positive"] == 2
        assert ps["A"]["windows_negative"] == 1
        assert ps["A"]["positive_rate"] == pytest.approx(66.7, abs=0.1)
        assert ps["B"]["windows_present"] == 1
        assert ps["B"]["windows_positive"] == 1
        assert ps["B"]["positive_rate"] == 100.0

    def test_per_regime_consistency(self):
        r = self._runner()
        # RANGING wins in all 3 windows; VOLATILE loses in 2
        t_r_win = {"pnl_usd": 50.0, "contributing_strategies": ["A"], "regime": "RANGING"}
        t_v_lose = {"pnl_usd": -30.0, "contributing_strategies": ["A"], "regime": "VOLATILE"}
        ws = [
            _mk_window(0, pnl=20, trades=[t_r_win, t_v_lose]),
            _mk_window(1, pnl=50, trades=[t_r_win]),
            _mk_window(2, pnl=20, trades=[t_r_win, t_v_lose]),
        ]
        agg = r.aggregate(ws)
        pr = agg["per_regime"]
        assert pr["RANGING"]["windows_present"] == 3
        assert pr["RANGING"]["windows_positive"] == 3
        assert pr["RANGING"]["positive_rate"] == 100.0
        assert pr["VOLATILE"]["windows_present"] == 2
        assert pr["VOLATILE"]["windows_negative"] == 2
        assert pr["VOLATILE"]["positive_rate"] == 0.0

    def test_multi_strategy_trade_credits_all(self):
        r = self._runner()
        t = {"pnl_usd": 60.0, "contributing_strategies": ["A", "B", "C"],
             "regime": "RANGING"}
        ws = [_mk_window(0, pnl=60, trades=[t])]
        agg = r.aggregate(ws)
        ps = agg["per_strategy"]
        for s in ("A", "B", "C"):
            assert ps[s]["windows_present"] == 1
            assert ps[s]["total_pnl"] == 60.0

    def test_missing_regime_defaults_to_unknown(self):
        r = self._runner()
        t = {"pnl_usd": 10.0, "contributing_strategies": ["A"]}  # no regime
        ws = [_mk_window(0, pnl=10, trades=[t])]
        agg = r.aggregate(ws)
        assert "UNKNOWN" in agg["per_regime"]