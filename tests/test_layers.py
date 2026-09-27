"""Integration tests for Layers 1-4."""
import pytest
from layers.layer1_account_rules import Layer1AccountRules
from layers.layer2_pricing import Layer2Pricing
from layers.layer3_strategies import Layer3Strategies
from layers.layer4_risk import Layer4Risk


def test_layer1_status():
    l1 = Layer1AccountRules("config/master.yaml")
    status = l1.status("personal")
    assert status["capital"] == 10000
    assert status["equity"] == 10000


def test_layer1_check_trade():
    l1 = Layer1AccountRules("config/master.yaml")
    ok, reason = l1.check_trade("personal", risk_amount=50.0, instrument="BTCUSD")
    assert ok, reason


def test_layer2_forward():
    l2 = Layer2Pricing()
    f = l2.forward(spot=100.0, risk_free_rate=0.05, time_to_maturity=1.0)
    # continuous compounding: 100 * e^0.05 = 105.127
    assert abs(f - 105.127) < 0.01


def test_layer3_registry_loads():
    l3 = Layer3Strategies(registry_root="strategies")
    assert l3.registry.count() > 0
    cands = l3.candidates("trending")
    assert len(cands) > 0


def test_layer4_position_size():
    l4 = Layer4Risk("config/master.yaml")
    size = l4.position_size(
        capital=10000, risk_pct=0.01, entry=100.0, stop=99.0,
    )
    # 1% of 10000 = $100 risk / $1 per unit = 100 units
    assert abs(size - 100.0) < 1e-6
