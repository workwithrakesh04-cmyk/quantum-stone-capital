"""Tests for beta_brain.jury.portfolio_jury."""
import pytest
from beta_brain.jury.portfolio_jury import PortfolioJury
from beta_brain.jury.transcript import RiskVerdict
from beta_brain.debate.transcript import DebateTranscript
from beta_brain.account_guard import reset_guards


def _config():
    return {
        "account": {"type": "personal", "account_type": "personal", "starting_balance": 10000},
        "account_rules": {"max_daily_loss_pct": 5.0, "max_total_drawdown_pct": 10.0},
        "risk": {"per_trade_pct": 2.0},
        "modes": {
            "scalp": {
                "enabled": True, "risk_per_trade_pct": 1.0, "min_rr": 1.5,
                "max_open_positions": 3, "max_notional_leverage": 10.0,
                "max_concurrent_risk_pct": 3.0,
            },
        },
        "daily_limits": {"max_daily_trades": 25, "disable_after_consecutive_losses": 6},
        "stop_loss": {"method": "atr", "atr_multiplier": 1.5, "percent_fallback": 0.3, "max_pct": 1.0},
        "loss_scaling": {"enabled": False},
    }


def _debate():
    return DebateTranscript(
        ts=1, symbol="BTCUSD", timeframe="5m", signals_input=[],
        rounds=[[], [], []], winner="BUY", winner_confidence=0.7,
        final_scores={"BUY": 0.7, "SELL": 0.1, "HOLD": 0.2},
    )


def _risk_approved(risk_usd=100, size_usd=1000):
    return RiskVerdict(
        approved=True, mode="scalp",
        position_size_usd=size_usd, position_size_qty=10,
        stop_loss_price=99, take_profit_price=101,
        risk_reward_ratio=1.5, risk_amount_usd=risk_usd,
    )


def setup_function(_):
    reset_guards()


def test_risk_not_approved_rejected():
    j = PortfolioJury(_config())
    r = RiskVerdict(approved=False, mode="scalp", reject_reason="test")
    v = j.evaluate(_debate(), r, {}, "scalp")
    assert v.approved is False


def test_ok_state_approved():
    j = PortfolioJury(_config())
    v = j.evaluate(_debate(), _risk_approved(), {"open_positions": 0}, "scalp")
    assert v.approved is True


def test_max_positions_reached_rejected():
    j = PortfolioJury(_config())
    v = j.evaluate(_debate(), _risk_approved(), {"open_positions": 3}, "scalp")
    assert v.approved is False
    assert "max 3" in v.reject_reason


def test_exposure_exceeded_rejected():
    j = PortfolioJury(_config())
    v = j.evaluate(
        _debate(), _risk_approved(risk_usd=500, size_usd=5000),
        {"open_positions": 0, "current_exposure_pct": 2.9}, "scalp",
    )
    assert v.approved is False
    assert "exposure" in v.reject_reason


def test_daily_loss_limit_rejected():
    j = PortfolioJury(_config())
    v = j.evaluate(
        _debate(), _risk_approved(),
        {"open_positions": 0, "daily_pnl_pct": -6.0}, "scalp",
    )
    assert v.approved is False
    assert "daily loss" in v.reject_reason


def test_disabled_mode_rejected():
    cfg = _config()
    cfg["modes"]["scalp"]["enabled"] = False
    j = PortfolioJury(cfg)
    v = j.evaluate(_debate(), _risk_approved(), {}, "scalp")
    assert v.approved is False


def test_notes_populated_on_approval():
    j = PortfolioJury(_config())
    v = j.evaluate(_debate(), _risk_approved(), {"open_positions": 0}, "scalp")
    assert v.approved is True
    assert len(v.notes) > 0


def test_guard_kill_switch_rejected():
    from beta_brain.account_guard import get_account_guard
    cfg = _config()
    cfg["account_rules"]["enable_kill_switch"] = True
    guard = get_account_guard(cfg)
    for _ in range(30):
        guard.record_trade(0)  # hit daily limit
    j = PortfolioJury(cfg)
    v = j.evaluate(_debate(), _risk_approved(), {"open_positions": 0}, "scalp")
    assert v.approved is False
