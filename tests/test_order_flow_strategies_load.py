"""Test that VPA and order flow strategies load via the registry."""
import pytest
from strategies.registry import StrategyRegistry


@pytest.fixture
def registry():
    return StrategyRegistry(root="strategies")


def test_vpa_strategies_present(registry):
    names = registry.all_names()
    for expected in ("vpa_stopping_volume", "vpa_absorption_reversal",
                     "vpa_no_demand_test", "vpa_no_supply_test"):
        assert expected in names, "missing: " + expected


def test_order_flow_strategies_present(registry):
    names = registry.all_names()
    for expected in ("footprint_absorption_reversal_bullish",
                     "footprint_absorption_reversal_bearish",
                     "cumulative_delta_divergence_bullish",
                     "cumulative_delta_divergence_bearish",
                     "footprint_imbalance_stack_buy",
                     "footprint_imbalance_stack_sell"):
        assert expected in names, "missing: " + expected


def test_vpa_count(registry):
    vpa = registry.by_category("vpa")
    assert len(vpa) >= 4


def test_order_flow_count(registry):
    of = registry.by_category("order_flow")
    assert len(of) >= 6
