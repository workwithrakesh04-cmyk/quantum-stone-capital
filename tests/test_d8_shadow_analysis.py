"""D8 tests - shadow_analysis (metrics + replay + comparison)."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backtest.shadow_analysis import (
    compute_metrics,
    replay_trades,
    print_comparison,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _mk_trade(entry=100.0, qty=1.0, pnl=10.0, exit_price=110.0,
              status="CLOSED_TP", direction="BUY"):
    return {
        "id": 1,
        "entry_price": entry,
        "qty": qty,
        "pnl_usd": pnl,
        "exit_price": exit_price,
        "status": status,
        "direction": direction,
    }


def _mk_decision(idx=500, open_time=1759000000000, close=100.0,
                 open_=100.0, high=100.0, low=100.0,
                 note="no_verdict", verdict=None, run_id="r1"):
    d = {
        "kind": "shadow_decision",
        "run_id": run_id,
        "candle_idx": idx,
        "candle_open_time": open_time,
        "candle_open": open_,
        "candle_high": high,
        "candle_low": low,
        "candle_close": close,
        "note": note,
        "balance": 10000.0,
        "open_trades": 0,
        "trade_id": None,
        "regime": None,
    }
    if verdict:
        d["verdict"] = verdict
    return d


def _mk_verdict_dict(winner="BUY", decision="APPROVED",
                     entry=100.0, sl=95.0, tp=110.0, qty=1.0):
    return {
        "ts": 1759000000000,
        "symbol": "BTCUSDT",
        "mode": "scalp",
        "account_type": "personal",
        "debate_winner": winner,
        "debate_confidence": 0.8,
        "final_decision": decision,
        "final_reason": "",
        "risk": {
            "approved": True,
            "mode": "scalp",
            "position_size_usd": entry * qty,
            "position_size_qty": qty,
            "stop_loss_price": sl,
            "take_profit_price": tp,
            "risk_reward_ratio": 1.5,
            "risk_amount_usd": 100.0,
        },
        "portfolio": {
            "approved": True,
        },
    }


# ----------------------------------------------------------------------
# compute_metrics
# ----------------------------------------------------------------------

class TestComputeMetrics:

    def test_empty_trades(self):
        m = compute_metrics([], starting_balance=10000.0)
        assert m["total_trades"] == 0
        assert m["ending_balance"] == 10000.0
        assert m["net_pnl"] == 0.0
        assert m["return_pct"] == 0.0
        assert m["win_rate"] == 0.0
        assert m["sharpe"] == 0.0

    def test_single_winner(self):
        m = compute_metrics([_mk_trade(pnl=100.0)],
                            starting_balance=10000.0)
        assert m["total_trades"] == 1
        assert m["wins"] == 1
        assert m["losses"] == 0
        assert m["net_pnl"] == 100.0
        assert m["ending_balance"] == 10100.0
        assert m["return_pct"] == 1.0
        assert m["win_rate"] == 100.0

    def test_single_loser(self):
        m = compute_metrics([_mk_trade(pnl=-50.0)],
                            starting_balance=10000.0)
        assert m["total_trades"] == 1
        assert m["wins"] == 0
        assert m["losses"] == 1
        assert m["net_pnl"] == -50.0
        assert m["win_rate"] == 0.0

    def test_profit_factor_50_50(self):
        trades = [_mk_trade(pnl=100.0), _mk_trade(pnl=-50.0),
                  _mk_trade(pnl=100.0), _mk_trade(pnl=-50.0)]
        m = compute_metrics(trades, starting_balance=10000.0)
        # gross profit 200, gross loss 100 -> PF 2.0
        assert m["profit_factor"] == 2.0

    def test_all_winners_pf_inf(self):
        trades = [_mk_trade(pnl=100.0), _mk_trade(pnl=50.0)]
        m = compute_metrics(trades, starting_balance=10000.0)
        assert m["profit_factor"] == "inf"

    def test_all_losers_pf_zero(self):
        trades = [_mk_trade(pnl=-100.0), _mk_trade(pnl=-50.0)]
        m = compute_metrics(trades, starting_balance=10000.0)
        assert m["profit_factor"] == 0.0

    def test_max_drawdown_computed(self):
        # Equity: 10000 -> 10100 -> 10050 -> 9950 -> 10000
        trades = [
            _mk_trade(pnl=100.0),
            _mk_trade(pnl=-50.0),
            _mk_trade(pnl=-100.0),
            _mk_trade(pnl=50.0),
        ]
        m = compute_metrics(trades, starting_balance=10000.0)
        # Peak 10100, trough 9950 -> dd 150, dd_pct = 150/10100*100 = 1.485
        assert m["max_drawdown_usd"] == 150.0
        assert pytest.approx(m["max_drawdown_pct"], abs=0.01) == 1.49

    def test_avg_win_avg_loss(self):
        trades = [
            _mk_trade(pnl=100.0), _mk_trade(pnl=200.0),
            _mk_trade(pnl=-50.0), _mk_trade(pnl=-100.0),
        ]
        m = compute_metrics(trades, starting_balance=10000.0)
        assert m["avg_win"] == 150.0
        assert m["avg_loss"] == -75.0

    def test_sharpe_computed_when_enough_trades(self):
        trades = [_mk_trade(pnl=p) for p in (100, -50, 80, -30, 120, -70)]
        m = compute_metrics(trades, starting_balance=10000.0,
                            period_days=1.0)
        # Just assert a finite non-crazy number
        assert isinstance(m["sharpe"], float)
        assert -100 < m["sharpe"] < 100


# ----------------------------------------------------------------------
# replay_trades
# ----------------------------------------------------------------------

class TestReplayTrades:

    def test_empty_decisions(self):
        assert replay_trades([]) == []

    def test_no_opened_records(self):
        decisions = [
            _mk_decision(idx=500, note="no_verdict"),
            _mk_decision(idx=501, note="no_verdict"),
        ]
        trades = replay_trades(decisions)
        assert trades == []

    def test_single_trade_opens_and_closes(self):
        # One "opened" candle, then EOD close
        v = _mk_verdict_dict(winner="BUY", entry=100.0, sl=95.0, tp=110.0)
        decisions = [
            _mk_decision(idx=500, close=100.0, note="opened", verdict=v),
            _mk_decision(idx=501, close=105.0, note="no_verdict"),
        ]
        trades = replay_trades(decisions)
        # Replay opens on idx=500, closes on end-of-run at close of idx=501
        # Expected pnl = (105 - 100) * qty = 5.0
        assert len(trades) == 1
        assert trades[0]["pnl_usd"] == 5.0

    def test_tp_hit_intrabar(self):
        v = _mk_verdict_dict(winner="BUY", entry=100.0, sl=95.0, tp=110.0)
        decisions = [
            _mk_decision(idx=500, close=100.0, high=100.0, low=100.0,
                         note="opened", verdict=v),
            # Next candle spikes to TP
            _mk_decision(idx=501, close=108.0, open_=100.0,
                         high=111.0, low=100.0, note="no_verdict"),
        ]
        trades = replay_trades(decisions)
        assert len(trades) == 1
        # TP hit at 110, pnl = (110 - 100) * 1 = 10
        assert trades[0]["pnl_usd"] == 10.0
        assert trades[0]["status"] == "CLOSED_TP"

    def test_sl_hit_intrabar(self):
        v = _mk_verdict_dict(winner="BUY", entry=100.0, sl=95.0, tp=110.0)
        decisions = [
            _mk_decision(idx=500, close=100.0, note="opened", verdict=v),
            _mk_decision(idx=501, close=97.0, open_=100.0,
                         high=100.0, low=93.0, note="no_verdict"),
        ]
        trades = replay_trades(decisions)
        assert len(trades) == 1
        assert trades[0]["pnl_usd"] == -5.0
        assert trades[0]["status"] == "CLOSED_SL"

    def test_hard_stop_closes_all(self):
        v = _mk_verdict_dict(winner="BUY", entry=100.0, sl=90.0, tp=120.0)
        decisions = [
            _mk_decision(idx=500, close=100.0, note="opened", verdict=v),
            _mk_decision(idx=501, close=99.0, note="hard_stop"),
            _mk_decision(idx=502, close=98.0, note="halted_skip"),
        ]
        trades = replay_trades(decisions)
        assert len(trades) == 1
        # Closed at hard stop candle's close (99.0)
        assert trades[0]["status"] == "CLOSED_EOD"

    def test_sell_direction(self):
        v = _mk_verdict_dict(winner="SELL", entry=100.0, sl=105.0, tp=90.0)
        decisions = [
            _mk_decision(idx=500, close=100.0, note="opened", verdict=v),
            _mk_decision(idx=501, close=95.0, note="no_verdict"),
        ]
        trades = replay_trades(decisions)
        assert len(trades) == 1
        # SELL at 100, close at 95 -> +5 * qty
        assert trades[0]["pnl_usd"] == 5.0

    def test_missing_ohlc_falls_back_to_close(self):
        # Old-style decisions with only close (no OHLC fields)
        v = _mk_verdict_dict(winner="BUY", entry=100.0, sl=95.0, tp=110.0)
        legacy_open = {
            "kind": "shadow_decision",
            "run_id": "r1",
            "candle_idx": 500,
            "candle_open_time": 1759000000000,
            "candle_close": 100.0,
            "note": "opened",
            "verdict": v,
        }
        legacy_noop = {
            "kind": "shadow_decision",
            "run_id": "r1",
            "candle_idx": 501,
            "candle_open_time": 1759000300000,
            "candle_close": 105.0,
            "note": "no_verdict",
        }
        trades = replay_trades([legacy_open, legacy_noop])
        assert len(trades) == 1
        assert trades[0]["pnl_usd"] == 5.0


# ----------------------------------------------------------------------
# print_comparison
# ----------------------------------------------------------------------

class TestPrintComparison:

    def test_returns_string(self):
        shadow = {"return_pct": 1.0, "total_trades": 5,
                  "win_rate": 60.0, "profit_factor": 1.5,
                  "max_drawdown_pct": 2.0, "sharpe": 0.5,
                  "sortino": 0.6, "calmar": 0.7}
        out = print_comparison(shadow)
        assert isinstance(out, str)
        assert "D8 SHADOW" in out
        assert "Return %" in out

    def test_includes_reference_label(self):
        out = print_comparison({}, reference_label="My Reference")
        assert "My Reference" in out

    def test_handles_missing_values(self):
        out = print_comparison({"return_pct": 1.0})
        assert "Return %" in out
        assert "-" in out  # missing keys print as "-"

    def test_handles_inf_profit_factor(self):
        out = print_comparison({
            "return_pct": 1.0, "total_trades": 5, "win_rate": 100.0,
            "profit_factor": float("inf"), "max_drawdown_pct": 0.0,
            "sharpe": 1.0, "sortino": 1.0, "calmar": 0.0,
        })
        assert isinstance(out, str)