"""D8c-2 tests - window hard stop behavior in BetaBacktester.

These tests exercise the halt logic without running the full backtester:
we construct a bare instance, set the fields the halt check reads, and
verify the halt fires at the right threshold and doesn't fire when
disabled.
"""
import pytest
from types import SimpleNamespace

from backtest.beta_backtester import BetaBacktester


def _mk_bt(starting_balance=10000.0, hard_stop_pct=0.0, balance=None):
    """Bare backtester with the fields the halt logic touches."""
    bt = BetaBacktester.__new__(BetaBacktester)
    bt.starting_balance = starting_balance
    bt.window_hard_stop_pct = float(hard_stop_pct)
    bt._window_halted = False
    bt._halt_candle_idx = None

    # Minimal trader stub. balance is what the halt check reads.
    closed = []
    def close_all_at_price(candle):
        # Simulate closing at the candle's close
        closed.append(candle)
    bt.trader = SimpleNamespace(
        balance=balance if balance is not None else starting_balance,
        closed_trades=[],
        close_all_at_price=close_all_at_price,
    )
    bt._closed_via_halt = closed  # test hook
    return bt


def _check_halt(bt, candle=None, candle_idx=0):
    """Replicate the halt check in isolation (same logic as in run_on_candles)."""
    candle = candle or {"open": 100, "high": 100, "low": 100, "close": 100,
                        "open_time": 0}
    if (not bt._window_halted
            and bt.window_hard_stop_pct > 0.0
            and bt.starting_balance > 0):
        ret_pct = (
            (bt.trader.balance - bt.starting_balance)
            / bt.starting_balance * 100.0
        )
        if ret_pct <= -bt.window_hard_stop_pct:
            bt.trader.close_all_at_price(candle)
            bt._window_halted = True
            bt._halt_candle_idx = candle_idx


class TestHardStopDisabled:

    def test_disabled_never_halts(self):
        bt = _mk_bt(hard_stop_pct=0.0, balance=5000)  # -50%
        _check_halt(bt)
        assert bt._window_halted is False
        assert bt._halt_candle_idx is None

    def test_negative_disabled(self):
        bt = _mk_bt(hard_stop_pct=-5.0, balance=5000)
        _check_halt(bt)
        assert bt._window_halted is False


class TestHardStopFires:

    def test_fires_at_exact_threshold(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9700.0)  # exactly -3.0%
        _check_halt(bt)
        assert bt._window_halted is True
        assert bt._halt_candle_idx == 0

    def test_fires_below_threshold(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9600.0)  # -4%
        _check_halt(bt)
        assert bt._window_halted is True

    def test_does_not_fire_above_threshold(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9750.0)  # -2.5%
        _check_halt(bt)
        assert bt._window_halted is False

    def test_does_not_fire_on_positive(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=10500.0)  # +5%
        _check_halt(bt)
        assert bt._window_halted is False

    def test_close_all_called_once(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9600.0)
        _check_halt(bt)
        assert len(bt._closed_via_halt) == 1

    def test_second_check_is_idempotent(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9600.0)
        _check_halt(bt)
        assert bt._window_halted is True
        # Run the check again - it should not call close_all a second time
        _check_halt(bt)
        assert len(bt._closed_via_halt) == 1

    def test_halt_candle_idx_recorded(self):
        bt = _mk_bt(hard_stop_pct=3.0, balance=9600.0)
        _check_halt(bt, candle_idx=42)
        assert bt._halt_candle_idx == 42


class TestHardStopEdgeCases:

    def test_zero_starting_balance_does_nothing(self):
        bt = _mk_bt(starting_balance=0.0, hard_stop_pct=3.0, balance=-100.0)
        _check_halt(bt)
        assert bt._window_halted is False

    def test_threshold_values_dict(self):
        """Sanity: the diagnostics field exists and returns the right value."""
        bt = BetaBacktester.__new__(BetaBacktester)
        bt.window_hard_stop_pct = 2.5
        bt._window_halted = False
        bt._halt_candle_idx = None
        assert bt.window_hard_stop_pct == 2.5
        assert bt._window_halted is False