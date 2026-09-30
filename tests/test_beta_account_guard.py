"""Tests for beta_brain.account_guard."""
import pytest
from beta_brain.account_guard import AccountGuard, AccountState, reset_guards, get_account_guard


def _personal_config():
    return {
        "account": {"type": "personal", "account_type": "personal", "starting_balance": 10000},
        "account_rules": {
            "max_daily_loss_pct": 5.0,
            "max_total_drawdown_pct": 10.0,
            "enable_kill_switch": False,
        },
        "daily_limits": {
            "max_daily_trades": 10,
            "disable_after_consecutive_losses": 3,
        },
    }


def _prop_config():
    return {
        "account": {"type": "prop", "account_type": "prop", "starting_balance": 10000},
        "account_rules": {
            "max_daily_loss_pct": 5.0,
            "max_total_drawdown_pct": 10.0,
            "enable_kill_switch": True,
        },
        "daily_limits": {
            "max_daily_trades": 5,
            "disable_after_consecutive_losses": 2,
        },
    }


def test_init_defaults():
    g = AccountGuard(_personal_config())
    assert g.state.current_balance == 10000
    assert g.state.peak_balance == 10000
    assert g.state.daily_trades == 0


def test_check_ok_initially():
    g = AccountGuard(_personal_config())
    ok, reason = g.check()
    assert ok is True


def test_personal_kill_switch_off_by_default():
    g = AccountGuard(_personal_config())
    assert g.enable_kill_switch is False


def test_prop_kill_switch_on_by_default():
    g = AccountGuard(_prop_config())
    assert g.enable_kill_switch is True


def test_daily_loss_warns_when_kill_switch_off():
    g = AccountGuard(_personal_config())
    g.record_trade(-600)
    ok, reason = g.check()
    assert ok is True
    assert "warned" in reason


def test_daily_loss_triggers_kill_on_prop():
    g = AccountGuard(_prop_config())
    g.record_trade(-600)
    ok, reason = g.check()
    assert ok is False
    assert g.state.kill_switch_triggered is True


def test_daily_trade_limit_personal():
    g = AccountGuard(_personal_config())
    for _ in range(10):
        g.record_trade(10)
    ok, reason = g.check()
    assert ok is False
    assert "daily trade limit" in reason


def test_consecutive_losses_block():
    g = AccountGuard(_personal_config())
    for _ in range(3):
        g.record_trade(-50)
    ok, reason = g.check()
    assert ok is False
    assert "consecutive losses" in reason


def test_consecutive_losses_reset_on_win():
    g = AccountGuard(_personal_config())
    g.record_trade(-50)
    g.record_trade(-50)
    g.record_trade(100)
    ok, reason = g.check()
    assert ok is True


def test_daily_reset_on_new_day():
    g = AccountGuard(_personal_config())
    g.record_trade(-50)
    assert g.state.consecutive_losses == 1
    g.daily_reset_if_needed(current_ts_ms=86400000 * 2)
    assert g.state.consecutive_losses == 0
    assert g.state.daily_trades == 0


def test_total_drawdown_warns():
    g = AccountGuard(_personal_config())
    g.record_trade(-1100)
    ok, reason = g.check()
    assert ok is True
    assert "warned" in reason


def test_snapshot_fields():
    g = AccountGuard(_personal_config())
    snap = g.snapshot()
    assert "current_balance" in snap
    assert "daily_pnl_pct" in snap
    assert "consecutive_losses" in snap
    assert "kill_switch_triggered" in snap


def test_get_account_guard_caches_by_type():
    reset_guards()
    g1 = get_account_guard(_personal_config())
    g2 = get_account_guard(_personal_config())
    assert g1 is g2


def test_reset_guards_clears_cache():
    reset_guards()
    g1 = get_account_guard(_personal_config())
    reset_guards()
    g2 = get_account_guard(_personal_config())
    assert g1 is not g2
