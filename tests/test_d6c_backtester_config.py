"""D6c tests - BetaBacktester config-driven max_hold_bars + stage counters."""
import pytest
from types import SimpleNamespace
import tempfile
import os
import yaml

from backtest.beta_backtester import BetaBacktester, TIMEFRAME_MINUTES


def _write_cfg(tmpdir, cfg: dict) -> str:
    path = os.path.join(tmpdir, "cfg.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    return path


def _mk_backtester(cfg: dict, timeframe: str = "5m", mode: str = "scalp"):
    """Build a BetaBacktester with a temp config, bypassing heavy __init__ work.

    We construct the object normally but immediately override the fields
    that D6c tests care about, to avoid loading 42 strategies per test.
    """
    with tempfile.TemporaryDirectory() as td:
        path = _write_cfg(td, cfg)
        bt = BetaBacktester.__new__(BetaBacktester)
        bt.symbol = "BTCUSDT"
        bt.timeframe = timeframe
        bt.account_type = "personal"
        bt.starting_balance = 10000.0
        bt.warmup = 100
        bt.max_window = 500
        bt.mode = mode
        bt.account_cfg = cfg
        bt.max_hold_bars = bt._derive_max_hold_bars()
        return bt


class TestMaxHoldBarsDerivation:

    def test_scalp_60min_5m(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"scalp": {"max_holding_minutes": 60}},
        }
        bt = _mk_backtester(cfg, timeframe="5m", mode="scalp")
        assert bt.max_hold_bars == 12  # 60 / 5

    def test_scalp_60min_1m(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"scalp": {"max_holding_minutes": 60}},
        }
        bt = _mk_backtester(cfg, timeframe="1m", mode="scalp")
        assert bt.max_hold_bars == 60

    def test_swing_hours(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"swing": {"max_holding_hours": 48}},
        }
        bt = _mk_backtester(cfg, timeframe="5m", mode="swing")
        # 48h * 60 / 5 = 576
        assert bt.max_hold_bars == 576

    def test_timeout_disabled_gives_zero(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": False},
            "modes": {"scalp": {"max_holding_minutes": 60}},
        }
        bt = _mk_backtester(cfg, timeframe="5m", mode="scalp")
        assert bt.max_hold_bars == 0

    def test_no_holding_key_gives_zero(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"scalp": {}},
        }
        bt = _mk_backtester(cfg, timeframe="5m", mode="scalp")
        assert bt.max_hold_bars == 0

    def test_unknown_timeframe_gives_zero(self):
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"scalp": {"max_holding_minutes": 60}},
        }
        bt = _mk_backtester(cfg, timeframe="7m", mode="scalp")
        assert bt.max_hold_bars == 0

    def test_never_returns_negative_or_zero_when_key_present(self):
        # If max_holding_minutes < tf_minutes, floor to 1 (never zero)
        cfg = {
            "account_rules": {"enable_timeout_exits": True},
            "modes": {"scalp": {"max_holding_minutes": 3}},
        }
        bt = _mk_backtester(cfg, timeframe="5m", mode="scalp")
        assert bt.max_hold_bars == 1


class TestStageCounters:

    def test_counters_initialized_to_zero(self):
        bt = BetaBacktester.__new__(BetaBacktester)
        bt.candles_processed = 0
        bt.debates_run = 0
        bt.trades_opened = 0
        bt.trades_rejected = 0
        bt.rejected_hold = 0
        bt.rejected_low_confidence = 0
        bt.rejected_risk_jury = 0
        bt.rejected_portfolio_jury = 0
        bt.max_hold_bars = 0
        # D7c: get_diagnostics now touches these two
        bt._debate_records = []
        bt.trader = SimpleNamespace(closed_trades=[])
        diag = bt.get_diagnostics()
        assert diag["rejected_hold"] == 0
        assert diag["rejected_low_confidence"] == 0
        assert diag["rejected_risk_jury"] == 0
        assert diag["rejected_portfolio_jury"] == 0
        assert diag["max_hold_bars_used"] == 0

    def test_diagnostics_shape(self):
        bt = BetaBacktester.__new__(BetaBacktester)
        bt.candles_processed = 9900
        bt.debates_run = 5623
        bt.trades_opened = 58
        bt.trades_rejected = 5565
        bt.rejected_hold = 100
        bt.rejected_low_confidence = 200
        bt.rejected_risk_jury = 4000
        bt.rejected_portfolio_jury = 1265
        bt.max_hold_bars = 12
        # D7c: get_diagnostics now touches these two
        bt._debate_records = []
        bt.trader = SimpleNamespace(closed_trades=[])
        diag = bt.get_diagnostics()
        for k in ("candles_processed", "debates_run", "trades_opened",
                  "trades_rejected", "rejected_hold", "rejected_low_confidence",
                  "rejected_risk_jury", "rejected_portfolio_jury",
                  "max_hold_bars_used"):
            assert k in diag
        assert diag["max_hold_bars_used"] == 12

    def test_timeframe_map_covers_common(self):
        for tf in ("1m", "5m", "15m", "1h"):
            assert tf in TIMEFRAME_MINUTES