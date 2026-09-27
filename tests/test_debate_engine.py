"""Tests for the Debate Engine and its components."""
import pytest
from workers.bull_bot import BullBot
from workers.bear_bot import BearBot
from workers.hold_bot import HoldBot
from jurors.risk_juror import RiskJuror
from jurors.strategy_juror import StrategyJuror
from jurors.execution_juror import ExecutionJuror
from core.debate_engine import DebateEngine, DebateResult


def test_bull_bot_bullish_context():
    bot = BullBot()
    arg = bot.analyze({"momentum": 0.05, "rsi": 25, "bos": "BOS_BULLISH",
                       "delta": 100, "passes_filter": True})
    assert arg.direction == "long"
    assert arg.confidence > 0.3


def test_bull_bot_bearish_context():
    bot = BullBot()
    arg = bot.analyze({"momentum": -0.05, "rsi": 75, "delta": -100})
    assert arg.direction == "flat"


def test_bear_bot_bearish_context():
    bot = BearBot()
    arg = bot.analyze({"momentum": -0.05, "rsi": 75, "bos": "BOS_BEARISH",
                       "delta": -100, "passes_filter": True})
    assert arg.direction == "short"
    assert arg.confidence > 0.3


def test_bear_bot_bullish_context():
    bot = BearBot()
    arg = bot.analyze({"momentum": 0.05, "rsi": 25, "delta": 100})
    assert arg.direction == "flat"


def test_hold_bot_flat_by_default():
    bot = HoldBot()
    arg = bot.analyze({})
    assert arg.direction == "flat"


def test_hold_bot_high_confidence_off_hours():
    bot = HoldBot()
    arg = bot.analyze({"session": "off_hours", "is_weekend": True,
                       "is_illiquid": True, "volatility": 0.10})
    assert arg.direction == "flat"
    assert arg.confidence >= 0.5


def test_risk_juror_approves_valid():
    j = RiskJuror()
    proposal = {"rr_ratio": 3.0, "risk_pct": 0.005, "daily_loss_pct": 0.0,
                "drawdown_pct": 0.02, "open_positions": 2, "stop_loss": 99.0}
    v = j.judge(proposal)
    assert v.approved


def test_risk_juror_rejects_low_rr():
    j = RiskJuror()
    v = j.judge({"rr_ratio": 1.0, "risk_pct": 0.005, "daily_loss_pct": 0.0,
                 "drawdown_pct": 0.02, "open_positions": 2, "stop_loss": 99.0})
    assert not v.approved


def test_risk_juror_rejects_missing_stop():
    j = RiskJuror()
    v = j.judge({"rr_ratio": 3.0, "risk_pct": 0.005, "daily_loss_pct": 0.0,
                 "drawdown_pct": 0.02, "open_positions": 2})
    assert not v.approved
    assert "stop_loss_missing" in v.warnings


def test_strategy_juror_approves_valid():
    j = StrategyJuror()
    v = j.judge({"strategy_name": "bb_9ema",
                 "strategy_regime": ["trending"],
                 "current_regime": "trending",
                 "confluence_score": 0.8,
                 "passes_filter": True,
                 "agreeing_frameworks": ["wyckoff", "smc"]})
    assert v.approved


def test_strategy_juror_rejects_regime_mismatch():
    j = StrategyJuror()
    v = j.judge({"strategy_name": "vcp",
                 "strategy_regime": ["trending"],
                 "current_regime": "ranging",
                 "confluence_score": 0.8})
    assert not v.approved


def test_execution_juror_approves_clean():
    j = ExecutionJuror()
    v = j.judge({"expected_slippage_pct": 0.0002, "expected_impact_pct": 0.0002,
                 "session": "london", "active_killzones": ["london_kz"],
                 "order_type": "limit"})
    assert v.approved


def test_execution_juror_rejects_high_slippage():
    j = ExecutionJuror()
    v = j.judge({"expected_slippage_pct": 0.01, "expected_impact_pct": 0.0002})
    assert not v.approved


def test_debate_flat_no_context():
    engine = DebateEngine()
    result = engine.debate({})
    assert result.direction == "flat"
    assert result.decision == "no_trade"


def test_debate_long_with_valid_proposal():
    engine = DebateEngine()
    context = {"momentum": 0.05, "rsi": 25, "bos": "BOS_BULLISH",
               "delta": 100, "passes_filter": True, "regime": "trending_up"}
    proposal = {
        "strategy_name": "bb_9ema",
        "strategy_regime": ["trending", "trending_up"],
        "current_regime": "trending_up",
        "confluence_score": 0.8,
        "passes_filter": True,
        "agreeing_frameworks": ["wyckoff", "smc"],
        "rr_ratio": 3.0, "risk_pct": 0.005, "daily_loss_pct": 0.0,
        "drawdown_pct": 0.02, "open_positions": 2, "stop_loss": 99.0,
        "expected_slippage_pct": 0.0002, "expected_impact_pct": 0.0002,
        "session": "london", "active_killzones": ["london_kz"],
        "order_type": "limit",
    }
    result = engine.debate(context, proposal)
    assert isinstance(result, DebateResult)
    assert result.direction == "long"
    assert result.decision == "trade"


def test_debate_blocked_by_risk_juror():
    engine = DebateEngine()
    context = {"momentum": 0.05, "rsi": 25, "bos": "BOS_BULLISH",
               "delta": 100, "passes_filter": True, "regime": "trending_up"}
    proposal = {
        "strategy_name": "bb_9ema",
        "strategy_regime": ["trending_up"],
        "current_regime": "trending_up",
        "confluence_score": 0.8,
        "passes_filter": True,
        "agreeing_frameworks": ["wyckoff", "smc"],
        "rr_ratio": 1.0,
        "risk_pct": 0.005, "daily_loss_pct": 0.0,
        "drawdown_pct": 0.02, "open_positions": 2, "stop_loss": 99.0,
    }
    result = engine.debate(context, proposal)
    assert result.decision == "no_trade"
    assert any("RR" in r for r in result.reasons)
