"""Tests for beta_brain.jury.risk_jury."""
import pytest
from beta_brain.jury.risk_jury import RiskJury
from beta_brain.debate.transcript import DebateTranscript
from beta_brain.account_guard import reset_guards


def _config():
    return {
        "account": {"type": "personal", "account_type": "personal", "starting_balance": 10000},
        "account_rules": {"max_daily_loss_pct": 5.0, "max_total_drawdown_pct": 10.0, "enable_kill_switch": False},
        "risk": {"per_trade_pct": 2.0},
        "modes": {
            "scalp": {
                "enabled": True, "risk_per_trade_pct": 1.0, "min_rr": 1.5,
                "max_open_positions": 3, "max_notional_leverage": 10.0,
                "max_concurrent_risk_pct": 3.0,
            },
            "swing": {
                "enabled": True, "risk_per_trade_pct": 2.0, "min_rr": 2.0,
                "max_open_positions": 1, "max_notional_leverage": 10.0,
                "max_concurrent_risk_pct": 2.0,
            },
        },
        "stop_loss": {"method": "atr", "atr_multiplier": 1.5, "percent_fallback": 0.3, "max_pct": 1.0},
        "loss_scaling": {"enabled": True, "thresholds": {3: 0.5, 5: 0.25, 7: 0.0}},
        "daily_limits": {"max_daily_trades": 25, "disable_after_consecutive_losses": 6},
    }


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def _candles(n=30, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, i * 300_000) for i in range(n)]


def _debate(winner):
    return DebateTranscript(
        ts=1, symbol="BTCUSD", timeframe="5m", signals_input=[],
        rounds=[[], [], []], winner=winner, winner_confidence=0.7,
        final_scores={"BUY": 0.7, "SELL": 0.1, "HOLD": 0.2},
    )


def setup_function(_):
    reset_guards()


def test_hold_winner_rejected():
    j = RiskJury(_config())
    v = j.evaluate(_debate("HOLD"), _candles(), 10000, "scalp")
    assert v.approved is False
    assert "HOLD" in v.reject_reason


def test_buy_approved_produces_sl_tp():
    j = RiskJury(_config())
    v = j.evaluate(_debate("BUY"), _candles(), 10000, "scalp")
    assert v.approved is True
    assert v.stop_loss_price > 0
    assert v.take_profit_price > v.stop_loss_price
    assert v.position_size_qty > 0


def test_sell_approved_produces_sl_above():
    j = RiskJury(_config())
    v = j.evaluate(_debate("SELL"), _candles(), 10000, "scalp")
    assert v.approved is True
    assert v.stop_loss_price > v.take_profit_price


def test_disabled_mode_rejected():
    cfg = _config()
    cfg["modes"]["scalp"]["enabled"] = False
    j = RiskJury(cfg)
    v = j.evaluate(_debate("BUY"), _candles(), 10000, "scalp")
    assert v.approved is False
    assert "disabled" in v.reject_reason


def test_no_candles_rejected():
    j = RiskJury(_config())
    v = j.evaluate(_debate("BUY"), [], 10000, "scalp")
    assert v.approved is False


def test_loss_scaling_reduces_risk():
    from beta_brain.account_guard import get_account_guard
    cfg = _config()
    guard = get_account_guard(cfg)
    for _ in range(3):
        guard.record_trade(-50)
    j = RiskJury(cfg)
    v = j.evaluate(_debate("BUY"), _candles(), 10000, "scalp")
    assert v.approved is True
    assert any("loss_scale" in n for n in v.notes)


def test_loss_scaling_blocked_at_zero():
    from beta_brain.account_guard import get_account_guard
    cfg = _config()
    guard = get_account_guard(cfg)
    for _ in range(7):
        guard.record_trade(-10)
    j = RiskJury(cfg)
    v = j.evaluate(_debate("BUY"), _candles(), 10000, "scalp")
    assert v.approved is False


def test_swing_mode_uses_swing_risk():
    j = RiskJury(_config())
    v = j.evaluate(_debate("BUY"), _candles(), 10000, "swing")
    assert v.approved is True
    assert v.risk_reward_ratio == 2.0


def test_short_history_fallback_sl():
    j = RiskJury(_config())
    candles = _candles(5)
    v = j.evaluate(_debate("BUY"), candles, 10000, "scalp")
    assert v.approved is True
    assert v.stop_loss_price > 0


def test_position_size_scales_with_equity():
    j = RiskJury(_config())
    v_small = j.evaluate(_debate("BUY"), _candles(), 5000, "scalp")
    j2 = RiskJury(_config())
    v_large = j2.evaluate(_debate("BUY"), _candles(), 20000, "scalp")
    assert v_large.position_size_qty > v_small.position_size_qty
