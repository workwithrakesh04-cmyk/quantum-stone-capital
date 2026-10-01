"""D7c tests - three new diagnostic aggregations on BetaBacktester.

These tests build a minimal backtester instance (no strategies loaded, no
data fetched) and populate `trader.closed_trades` and `_debate_records`
directly, then assert the aggregation methods behave correctly.
"""
import pytest
from types import SimpleNamespace

from backtest.beta_backtester import BetaBacktester, CONF_BUCKETS


def _mk_bt():
    """Construct a bare backtester without __init__ heavy work."""
    bt = BetaBacktester.__new__(BetaBacktester)
    bt._debate_records = []
    bt.trader = SimpleNamespace(closed_trades=[])
    return bt


def _mk_trade(direction="BUY", status="CLOSED_TP", pnl=100.0,
              regime="RANGING", bars=1, strategies=None):
    return SimpleNamespace(
        direction=direction,
        status=status,
        pnl_usd=pnl,
        regime=regime,
        bars_held=bars,
        contributing_strategies=list(strategies or []),
    )


class TestConfidenceHistogram:

    def test_empty(self):
        bt = _mk_bt()
        h = bt.confidence_histogram()
        assert h["n_buy_sell_debates"] == 0
        assert h["n_passed_gate"] == 0
        assert h["n_rejected_by_gate"] == 0
        assert h["mean_confidence"] == 0.0
        assert h["median_confidence"] == 0.0

    def test_hold_debates_excluded(self):
        bt = _mk_bt()
        bt._debate_records = [
            {"winner": "HOLD", "confidence": 0.9, "min_conf": 0.7,
             "passed_gate": True, "regime": "RANGING"},
            {"winner": "BUY",  "confidence": 0.75, "min_conf": 0.7,
             "passed_gate": True, "regime": "RANGING"},
        ]
        h = bt.confidence_histogram()
        assert h["n_buy_sell_debates"] == 1
        assert h["n_passed_gate"] == 1

    def test_buckets_place_correctly(self):
        bt = _mk_bt()
        bt._debate_records = [
            {"winner": "BUY",  "confidence": 0.35, "min_conf": 0.7,
             "passed_gate": False, "regime": "RANGING"},
            {"winner": "SELL", "confidence": 0.55, "min_conf": 0.7,
             "passed_gate": False, "regime": "RANGING"},
            {"winner": "BUY",  "confidence": 0.75, "min_conf": 0.7,
             "passed_gate": True,  "regime": "RANGING"},
            {"winner": "SELL", "confidence": 0.95, "min_conf": 0.7,
             "passed_gate": True,  "regime": "RANGING"},
        ]
        h = bt.confidence_histogram()
        assert h["n_buy_sell_debates"] == 4
        assert h["n_passed_gate"] == 2
        assert h["n_rejected_by_gate"] == 2
        # 0.35 in 0.3-0.4; 0.55 in 0.5-0.6; 0.75 in 0.7-0.8; 0.95 in 0.9-1.0
        assert h["buckets_all"]["0.3-0.4"] == 1
        assert h["buckets_all"]["0.5-0.6"] == 1
        assert h["buckets_all"]["0.7-0.8"] == 1
        assert h["buckets_all"]["0.9-1.0"] == 1
        assert h["buckets_passed"]["0.7-0.8"] == 1
        assert h["buckets_rejected"]["0.3-0.4"] == 1
        assert h["buckets_rejected"]["0.5-0.6"] == 1

    def test_boundary_value_belongs_to_upper_bucket(self):
        # 0.7 exactly should land in 0.7-0.8 (>= lower edge)
        bt = _mk_bt()
        bt._debate_records = [
            {"winner": "BUY", "confidence": 0.7, "min_conf": 0.7,
             "passed_gate": True, "regime": "RANGING"},
        ]
        h = bt.confidence_histogram()
        assert h["buckets_all"]["0.7-0.8"] == 1

    def test_mean_and_median(self):
        bt = _mk_bt()
        confs = [0.4, 0.5, 0.6, 0.7, 0.8]
        bt._debate_records = [
            {"winner": "BUY", "confidence": c, "min_conf": 0.7,
             "passed_gate": c >= 0.7, "regime": "RANGING"}
            for c in confs
        ]
        h = bt.confidence_histogram()
        assert h["n_buy_sell_debates"] == 5
        assert pytest.approx(h["mean_confidence"], abs=1e-3) == 0.6
        assert pytest.approx(h["median_confidence"], abs=1e-3) == 0.6


class TestVolatileByStrategy:

    def test_empty(self):
        bt = _mk_bt()
        assert bt.volatile_by_strategy() == {}

    def test_only_volatile_regime_counted(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(regime="VOLATILE",  pnl=100, strategies=["a"]),
            _mk_trade(regime="RANGING",   pnl=100, strategies=["a"]),
            _mk_trade(regime="TRENDING_UP", pnl=100, strategies=["a"]),
        ]
        out = bt.volatile_by_strategy()
        assert "a" in out
        assert out["a"]["trades"] == 1
        assert out["a"]["wins"] == 1

    def test_pnl_sums_correctly(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(regime="VOLATILE", pnl=100, strategies=["a"]),
            _mk_trade(regime="VOLATILE", pnl=-40, strategies=["a"]),
            _mk_trade(regime="VOLATILE", pnl=-10, strategies=["b"]),
        ]
        out = bt.volatile_by_strategy()
        assert out["a"]["trades"] == 2
        assert out["a"]["wins"] == 1
        assert out["a"]["losses"] == 1
        assert pytest.approx(out["a"]["pnl_usd"], abs=1e-2) == 60.0
        assert out["a"]["win_rate"] == 50.0
        assert out["b"]["trades"] == 1
        assert out["b"]["pnl_usd"] == -10.0
        assert out["b"]["win_rate"] == 0.0

    def test_multi_strategy_trade_credits_each(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(regime="VOLATILE", pnl=50, strategies=["a", "b", "c"]),
        ]
        out = bt.volatile_by_strategy()
        for s in ("a", "b", "c"):
            assert out[s]["trades"] == 1
            assert pytest.approx(out[s]["pnl_usd"], abs=1e-2) == 50.0


class TestTmoByStrategy:

    def test_empty(self):
        bt = _mk_bt()
        assert bt.tmo_by_strategy() == {}

    def test_only_tmo_counted(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(status="CLOSED_TP",      pnl=100, strategies=["a"]),
            _mk_trade(status="CLOSED_SL",      pnl=-50, strategies=["a"]),
            _mk_trade(status="CLOSED_TIMEOUT", pnl=20,  strategies=["a"]),
        ]
        out = bt.tmo_by_strategy()
        assert out["a"]["trades"] == 1
        assert out["a"]["pnl_usd"] == 20.0

    def test_avg_bars(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(status="CLOSED_TIMEOUT", pnl=10, bars=10, strategies=["a"]),
            _mk_trade(status="CLOSED_TIMEOUT", pnl=10, bars=20, strategies=["a"]),
        ]
        out = bt.tmo_by_strategy()
        assert out["a"]["trades"] == 2
        assert out["a"]["avg_bars"] == 15.0
        # bars_total key must be deleted
        assert "bars_total" not in out["a"]

    def test_multi_strategy_tmo(self):
        bt = _mk_bt()
        bt.trader.closed_trades = [
            _mk_trade(status="CLOSED_TIMEOUT", pnl=-30, bars=12,
                      strategies=["flag_limits", "rbd_dbr"]),
        ]
        out = bt.tmo_by_strategy()
        assert out["flag_limits"]["trades"] == 1
        assert out["flag_limits"]["pnl_usd"] == -30.0
        assert out["rbd_dbr"]["trades"] == 1
        assert out["rbd_dbr"]["pnl_usd"] == -30.0


class TestDiagnosticsShape:

    def test_get_diagnostics_includes_d7c_keys(self):
        bt = _mk_bt()
        bt.candles_processed = 0
        bt.debates_run = 0
        bt.trades_opened = 0
        bt.trades_rejected = 0
        bt.rejected_hold = 0
        bt.rejected_low_confidence = 0
        bt.rejected_risk_jury = 0
        bt.rejected_portfolio_jury = 0
        bt.max_hold_bars = 12
        d = bt.get_diagnostics()
        for k in ("confidence_histogram", "volatile_by_strategy", "tmo_by_strategy"):
            assert k in d
        # All three should be empty dicts / zero-count structures on a
        # fresh instance with no trades.
        assert d["volatile_by_strategy"] == {}
        assert d["tmo_by_strategy"] == {}
        assert d["confidence_histogram"]["n_buy_sell_debates"] == 0

    def test_conf_buckets_constant(self):
        assert CONF_BUCKETS[0] == 0.0
        assert CONF_BUCKETS[-1] > 1.0