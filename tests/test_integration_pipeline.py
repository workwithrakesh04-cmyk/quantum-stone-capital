"""Full-stack integration tests across all layers."""
import numpy as np
import pytest

from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2
from core.debate_engine import DebateEngine
from layers.layer0_data import CSVDataFeed
from layers.layer1_account_rules import Layer1AccountRules
from layers.layer2_pricing import Layer2Pricing
from layers.layer3_strategies import Layer3Strategies
from layers.layer4_risk import Layer4Risk
from layers.layer5_execution import Layer5Execution
from layers.layer6_order_flow import Layer6OrderFlow


@pytest.fixture
def brain():
    return MainBrainV2()


def _ctx_from_csv():
    """Build a MarketContext from the sample BTCUSD CSV."""
    feed = CSVDataFeed(data_dir="data/raw")
    feed.connect()
    bars = feed.get_bars("BTCUSD", "5m", count=120)
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    opens = [b.open for b in bars]
    volumes = [b.volume for b in bars]
    momentum = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0.0
    return MarketContext(
        symbol="BTCUSD",
        timeframe="5m",
        closes=closes, highs=highs, lows=lows, opens=opens, volumes=volumes,
        momentum=momentum, rsi=50.0, delta=0.0,
        regime="trending_up", session="london",
        active_killzones=["london_kz"], passes_filter=True,
        agreeing_frameworks=["wyckoff", "smc"],
    )


def test_full_pipeline_from_csv(brain):
    ctx = _ctx_from_csv()
    result = brain.run(ctx)
    assert result.decision in ("trade", "no_trade")
    assert "layer7_main_brain" in result.layers_passed


def test_layer1_via_full_stack():
    l1 = Layer1AccountRules("config/master.yaml")
    ok, reason = l1.check_trade("personal", risk_amount=50.0, instrument="BTCUSD")
    assert ok, reason


def test_layer2_and_layer3_stack():
    l2 = Layer2Pricing()
    l3 = Layer3Strategies(registry_root="strategies")
    f = l2.forward(spot=100.0, risk_free_rate=0.05, time_to_maturity=1.0)
    assert f > 100.0
    assert l3.registry.count() > 0


def test_layer4_and_layer5_stack():
    l4 = Layer4Risk("config/master.yaml")
    l5 = Layer5Execution("config/master.yaml")
    size = l4.position_size(capital=10000, risk_pct=0.01, entry=100.0, stop=99.0)
    assert size > 0
    children = l5.split(size, avg_volume=100000)
    assert sum(children) == size


def test_layer6_order_flow_stack():
    l6 = Layer6OrderFlow()
    bar = l6.bar(bid_volume=100, ask_volume=150, high=101, low=99, close=100.5)
    assert bar.delta == 50


def test_debate_engine_standalone():
    engine = DebateEngine()
    context = {
        "momentum": 0.05, "rsi": 25, "bos": "BOS_BULLISH",
        "delta": 100, "passes_filter": True, "regime": "trending_up",
    }
    result = engine.debate(context)
    # Without proposal, jury doesn't run but direction is set
    assert result.direction in ("long", "short", "flat")


def test_pipeline_deterministic_for_same_input(brain):
    ctx1 = _ctx_from_csv()
    ctx2 = _ctx_from_csv()
    r1 = brain.run(ctx1)
    r2 = brain.run(ctx2)
    assert r1.direction == r2.direction
    assert r1.decision == r2.decision


def test_pipeline_layers_passed_order(brain):
    ctx = _ctx_from_csv()
    result = brain.run(ctx)
    # Layer order should be monotonic (0 -> 1 -> 2 -> 3 -> 4 -> 6 -> 7)
    order = ["layer0_data", "layer1_account_rules", "layer2_pricing",
             "layer3_strategies", "layer4_routing", "layer6_debate", "layer7_main_brain"]
    for i, name in enumerate(order):
        assert result.layers_passed[i] == name, "wrong order at " + name
