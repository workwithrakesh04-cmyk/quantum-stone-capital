"""End-to-end hybrid integration smoke tests."""
from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2
from beta_brain.beta_brain import BetaBrain
from consensus.arbiter import ConsensusArbiter


def _make_context():
    closes = [100.0 + i * 0.1 for i in range(150)]
    return MarketContext(
        symbol="BTCUSD",
        timeframe="5m",
        closes=closes,
        highs=[c * 1.005 for c in closes],
        lows=[c * 0.995 for c in closes],
        opens=list(closes),
        volumes=[1.0] * len(closes),
        momentum=0.005,
        rsi=55.0,
        delta=0.0,
        volatility=0.01,
        regime="trending_up",
        session="london",
    )


def test_main_brain_v2_still_works():
    brain = MainBrainV2()
    ctx = _make_context()
    result = brain.run(ctx, account_name="personal")
    assert result is not None
    assert hasattr(result, "decision")


def test_beta_brain_runs_on_market_context():
    bb = BetaBrain()
    ctx = _make_context()
    verdict = bb.run(ctx)
    assert verdict is None or hasattr(verdict, "final_decision")


def test_arbiter_combines_qsc_and_beta():
    qsc = MainBrainV2()
    bb = BetaBrain()
    arb = ConsensusArbiter()

    ctx = _make_context()
    qsc_result = qsc.run(ctx, account_name="personal")
    beta_verdict = bb.run(ctx)
    decision = arb.decide(qsc_result, beta_verdict)

    assert decision.consensus in (
        "BOTH_AGREE", "QSC_ONLY", "BETA_ONLY", "DISAGREE", "BOTH_HOLD"
    )
    assert decision.direction in ("LONG", "SHORT", "HOLD")
    assert 0.0 <= decision.size_multiplier <= 1.0


def test_arbiter_attached_to_metadata_when_beta_enabled():
    brain = MainBrainV2()
    ctx = _make_context()
    result = brain.run(ctx, account_name="personal")
    if "arbiter" in result.metadata:
        arb = result.metadata["arbiter"]
        assert "consensus" in arb
        assert "size_multiplier" in arb


def test_hybrid_never_breaks_qsc():
    brain = MainBrainV2()
    bad_ctx = MarketContext(symbol="BTCUSD", timeframe="5m", closes=[])
    result = brain.run(bad_ctx, account_name="personal")
    assert result is not None
    assert result.decision in ("trade", "no_trade")


def test_arbiter_returns_decision_object():
    arb = ConsensusArbiter()
    decision = arb.decide(None, None)
    assert isinstance(decision.to_dict(), dict)
    assert decision.consensus == "BOTH_HOLD"


def test_run_hybrid_module_imports():
    import importlib
    mod = importlib.import_module("scripts.run_hybrid")
    assert hasattr(mod, "main")
    assert hasattr(mod, "run_once")
    assert hasattr(mod, "build_context")


def test_hybrid_decision_dataclass_extended():
    from dashboard.state import Decision
    d = Decision(
        symbol="BTCUSD", direction="long", confidence=0.7,
        decision="trade", strategy_name="test",
        alpha_direction="LONG", alpha_confidence=0.7,
        beta_direction="LONG", beta_confidence=0.6,
        consensus="BOTH_AGREE", size_multiplier=1.0,
    )
    assert d.consensus == "BOTH_AGREE"
    assert d.size_multiplier == 1.0
