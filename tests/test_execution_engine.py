"""Tests for ExecutionEngine."""
import pytest
from core.execution_engine import ExecutionEngine
from core.order import Order, OrderType, OrderSide, OrderStatus


@pytest.fixture
def engine():
    return ExecutionEngine(max_slippage_pct=0.001, commission_per_unit=0.0001)


def test_slippage_zero_volume(engine):
    s = engine.compute_slippage(mid_price=100.0, order_size=1.0, avg_volume=0.0, volatility=1.0)
    assert s == 0.001


def test_slippage_small_order(engine):
    s = engine.compute_slippage(mid_price=100.0, order_size=1.0, avg_volume=100000.0, volatility=0.1)
    assert 0.0 <= s <= 0.001


def test_slippage_capped(engine):
    s = engine.compute_slippage(mid_price=100.0, order_size=100000.0, avg_volume=100.0, volatility=10.0)
    assert s == 0.001


def test_split_small_order(engine):
    children = engine.split_order(total_size=10.0, avg_volume=100000.0, max_participation=0.001)
    assert children == [10.0]


def test_split_large_order(engine):
    children = engine.split_order(total_size=1000.0, avg_volume=100.0, max_participation=0.001)
    # max_child = 0.1, so 1000 / 0.1 = 10000 children
    assert len(children) > 1
    assert abs(sum(children) - 1000.0) < 1e-6


def test_split_zero_volume(engine):
    children = engine.split_order(total_size=100.0, avg_volume=0.0)
    assert children == [100.0]


def test_split_zero_size(engine):
    children = engine.split_order(total_size=0.0, avg_volume=100.0)
    assert children == [0.0]


def test_simulate_fill_buy(engine):
    order = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=10.0)
    filled = engine.simulate_fill(order, mid_price=100.0, avg_volume=100000.0, volatility=0.1)
    assert filled.status == OrderStatus.FILLED
    assert filled.fill_price >= 100.0  # BUY slips up
    assert filled.slippage >= 0.0
    assert filled.commission > 0.0


def test_simulate_fill_sell(engine):
    order = Order(symbol="BTCUSD", side=OrderSide.SELL, order_type=OrderType.MARKET, size=10.0)
    filled = engine.simulate_fill(order, mid_price=100.0, avg_volume=100000.0, volatility=0.1)
    assert filled.status == OrderStatus.FILLED
    assert filled.fill_price <= 100.0  # SELL slips down


def test_notional_after_fill(engine):
    order = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=10.0)
    filled = engine.simulate_fill(order, mid_price=100.0, avg_volume=100000.0, volatility=0.1)
    assert filled.notional > 0


def test_round_trip_cost_shape(engine):
    cost = engine.round_trip_cost(order_size=10.0, mid_price=100.0, avg_volume=100000.0, volatility=0.1)
    assert "one_way_slippage_pct" in cost
    assert "one_way_cost" in cost
    assert "round_trip_cost" in cost
    assert "commission" in cost


def test_round_trip_cost_positive(engine):
    cost = engine.round_trip_cost(order_size=10.0, mid_price=100.0, avg_volume=100000.0, volatility=0.1)
    assert cost["round_trip_cost"] >= 0.0


def test_order_type_enum():
    assert OrderType.MARKET.value == "market"
    assert OrderType.STOP_LIMIT.value == "stop_limit"


def test_order_side_enum():
    assert OrderSide.BUY.value == "buy"
    assert OrderSide.SELL.value == "sell"


def test_order_status_default():
    order = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=1.0)
    assert order.status == OrderStatus.PENDING
