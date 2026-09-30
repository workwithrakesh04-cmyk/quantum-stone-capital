"""Tests for beta_brain.jury.verdict_engine."""
import pytest
from beta_brain.jury.verdict_engine import VerdictEngine
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


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def _candles(n=30, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, i * 300_000) for i in range(n)]


def _debate(winner="BUY"):
    return DebateTranscript(
        ts=1, symbol="BTCUSD", timeframe="5m", signals_input=[],
        rounds=[[], [], []], winner=winner, winner_confidence=0.7,
        final_scores={"BUY": 0.7, "SELL": 0.1, "HOLD": 0.2},
    )


def setup_function(_):
    reset_guards()


def test_verdict_engine_buy_approves():
    ve = VerdictEngine(config=_config())
    v = ve.run(_debate("BUY"), _candles(), equity=10000, mode="scalp")
    assert v.final_decision == "APPROVED"
    assert v.debate_winner == "BUY"


def test_verdict_engine_hold_rejected():
    ve = VerdictEngine(config=_config())
    v = ve.run(_debate("HOLD"), _candles(), equity=10000, mode="scalp")
    assert v.final_decision == "REJECTED"


def test_verdict_engine_sell_approves():
    ve = VerdictEngine(config=_config())
    v = ve.run(_debate("SELL"), _candles(), equity=10000, mode="scalp")
    assert v.final_decision == "APPROVED"


def test_verdict_engine_missing_config_raises():
    ve = VerdictEngine()
    with pytest.raises(ValueError):
        ve.run(_debate("BUY"), _candles(), equity=10000, account_type="prop")


def test_set_config_multiple_accounts():
    ve = VerdictEngine()
    ve.set_config("personal", _config())
    ve.set_config("prop", _config())
    v1 = ve.run(_debate("BUY"), _candles(), equity=10000, account_type="personal")
    v2 = ve.run(_debate("BUY"), _candles(), equity=10000, account_type="prop")
    assert v1.final_decision == "APPROVED"
    assert v2.final_decision == "APPROVED"


def test_account_snapshot():
    ve = VerdictEngine(config=_config())
    snap = ve.account_snapshot("personal")
    assert "current_balance" in snap
    assert snap["current_balance"] == 10000


def test_verdict_has_symbol_and_mode():
    ve = VerdictEngine(config=_config())
    v = ve.run(_debate("BUY"), _candles(), equity=10000, mode="scalp")
    assert v.symbol == "BTCUSD"
    assert v.mode == "scalp"


def test_verdict_risk_fields_populated():
    ve = VerdictEngine(config=_config())
    v = ve.run(_debate("BUY"), _candles(), equity=10000, mode="scalp")
    assert v.risk.approved is True
    assert v.risk.position_size_qty > 0
    assert v.portfolio.approved is True
