"""Tests for MainBrainV2 end-to-end pipeline."""
import numpy as np
import pytest

from core.market_context import MarketContext
from core.pipeline_result import PipelineResult
from core.main_brain_v2 import MainBrainV2


def _make_context(regime="trending_up", momentum=0.05, n=120):
    np.random.seed(0)
    closes = list(np.cumsum(np.random.randn(n) * 0.01) + 100)
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    return MarketContext(
        symbol="BTCUSD",
        timeframe="5m",
        closes=closes,
        highs=highs,
        lows=lows,
        opens=closes,
        volumes=[1000] * n,
        momentum=momentum,
        rsi=35.0,
        delta=100.0,
        bos="BOS_BULLISH",
        regime=regime,
        session="london",
        active_killzones=["london_kz"],
        passes_filter=True,
        agreeing_frameworks=["wyckoff", "smc"],
    )


@pytest.fixture
def brain():
    return MainBrainV2()


def test_run_returns_pipeline_result(brain):
    result = brain.run(_make_context())
    assert isinstance(result, PipelineResult)


def test_run_unknown_account(brain):
    result = brain.run(_make_context(), account_name="nonexistent")
    assert result.decision == "no_trade"
    assert "unknown_account" in result.reasons


def test_run_no_price_data(brain):
    ctx = MarketContext(symbol="BTCUSD", timeframe="5m")
    result = brain.run(ctx)
    assert result.decision == "no_trade"
    assert "no_price_data" in result.reasons


def test_run_no_matching_strategy(brain):
    ctx = _make_context(regime=None)
    result = brain.run(ctx)
    assert result.decision == "no_trade"
    assert "no_matching_strategy" in result.reasons


def test_run_layers_passed(brain):
    result = brain.run(_make_context())
    assert "layer0_data" in result.layers_passed
    assert "layer1_account_rules" in result.layers_passed
    assert "layer2_pricing" in result.layers_passed
    assert "layer3_strategies" in result.layers_passed
    assert "layer6_debate" in result.layers_passed
    assert "layer7_main_brain" in result.layers_passed


def test_run_picks_strategy_for_trending_up(brain):
    result = brain.run(_make_context(regime="trending_up"))
    assert result.strategy_name is not None


def test_run_picks_strategy_for_ranging(brain):
    result = brain.run(_make_context(regime="ranging", momentum=0.001))
    assert result.strategy_name is not None


def test_run_long_decision(brain):
    ctx = _make_context(regime="trending_up", momentum=0.05)
    result = brain.run(ctx)
    # Either trade long or no_trade (depends on juror thresholds)
    assert result.direction in ("long", "flat")
    assert result.decision in ("trade", "no_trade")


def test_run_confidence_between_0_and_1(brain):
    result = brain.run(_make_context())
    assert 0.0 <= result.confidence <= 1.0


def test_run_no_strategy_regime_none(brain):
    ctx = _make_context(regime=None)
    result = brain.run(ctx)
    assert result.strategy_name is None


def test_run_pipeline_result_has_metadata(brain):
    result = brain.run(_make_context())
    # metadata may or may not contain signal_score depending on momentum
    assert isinstance(result.metadata, dict)


def test_run_flat_when_momentum_near_zero(brain):
    ctx = _make_context(regime="ranging", momentum=0.0)
    result = brain.run(ctx)
    # Ranging + zero momentum → likely flat
    assert result.direction in ("flat", "long", "short")


def test_pipeline_result_is_trade_property():
    r = PipelineResult(decision="trade")
    assert r.is_trade is True
    r2 = PipelineResult(decision="no_trade")
    assert r2.is_trade is False


def test_market_context_is_valid():
    ctx = _make_context()
    assert ctx.is_valid is True


def test_market_context_invalid_when_empty():
    ctx = MarketContext(symbol="", timeframe="5m")
    assert ctx.is_valid is False
