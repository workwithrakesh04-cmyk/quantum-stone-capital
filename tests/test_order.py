"""Tests for Order dataclass and enums."""
import pytest
from datetime import datetime, timezone
from core.order import Order, OrderType, OrderSide, OrderStatus


def test_order_default_status():
    o = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=1.0)
    assert o.status == OrderStatus.PENDING


def test_order_timestamp_is_utc():
    o = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=1.0)
    assert o.timestamp.tzinfo is not None


def test_order_notional_zero_before_fill():
    o = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=1.0)
    assert o.notional == 0.0


def test_order_notional_after_fill():
    o = Order(symbol="BTCUSD", side=OrderSide.BUY, order_type=OrderType.MARKET, size=10.0)
    o.fill_price = 100.0
    assert o.notional == 1000.0


def test_order_types_cover_all():
    types = [t.value for t in OrderType]
    for expected in ["market", "limit", "stop", "stop_limit", "mit", "fok", "gtc"]:
        assert expected in types


def test_order_sides():
    sides = [s.value for s in OrderSide]
    assert "buy" in sides
    assert "sell" in sides


def test_order_statuses():
    statuses = [s.value for s in OrderStatus]
    for expected in ["pending", "submitted", "partial", "filled", "cancelled", "rejected"]:
        assert expected in statuses


def test_order_optional_fields_default_none():
    o = Order(symbol="EURUSD", side=OrderSide.SELL, order_type=OrderType.LIMIT, size=1000.0)
    assert o.limit_price is None
    assert o.stop_price is None
    assert o.fill_price is None
    assert o.strategy is None
    assert o.notes is None
