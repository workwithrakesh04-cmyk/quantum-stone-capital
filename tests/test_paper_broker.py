"""Tests for PaperBroker."""
import pytest
from brokers.paper_broker import PaperBroker
from brokers.base_broker import BrokerAccount, BrokerOrder


@pytest.fixture
def broker():
    b = PaperBroker(starting_balance=10000.0, prices={"BTCUSD": 40000.0})
    b.connect()
    return b


def test_connect(broker):
    assert broker._connected is True


def test_disconnect(broker):
    broker.disconnect()
    assert broker._connected is False


def test_account_initial(broker):
    info = broker.account_info()
    assert isinstance(info, BrokerAccount)
    assert info.balance == 10000.0
    assert info.equity == 10000.0


def test_last_price(broker):
    assert broker.last_price("BTCUSD") == 40000.0


def test_last_price_unknown_symbol(broker):
    assert broker.last_price("UNKNOWN") is None


def test_open_order_when_not_connected():
    b = PaperBroker(prices={"BTCUSD": 100.0})
    # not connected
    result = b.open_order("BTCUSD", "buy", 1.0)
    assert result is None


def test_open_buy_order(broker):
    order = broker.open_order("BTCUSD", "buy", 0.01)
    assert order is not None
    assert isinstance(order, BrokerOrder)
    assert order.side == "buy"
    assert order.status == "open"


def test_open_sell_order(broker):
    order = broker.open_order("BTCUSD", "sell", 0.01)
    assert order.side == "sell"


def test_open_order_invalid_side(broker):
    assert broker.open_order("BTCUSD", "hold", 1.0) is None


def test_open_order_unknown_symbol(broker):
    assert broker.open_order("UNKNOWN", "buy", 1.0) is None


def test_open_order_zero_volume(broker):
    assert broker.open_order("BTCUSD", "buy", 0.0) is None


def test_list_open_orders(broker):
    broker.open_order("BTCUSD", "buy", 0.01)
    broker.open_order("BTCUSD", "sell", 0.01)
    assert len(broker.open_orders()) == 2


def test_close_order(broker):
    order = broker.open_order("BTCUSD", "buy", 0.01)
    assert broker.close_order(order.ticket) is True
    assert len(broker.open_orders()) == 0


def test_close_nonexistent_order(broker):
    assert broker.close_order(999) is False


def test_profit_on_price_move(broker):
    order = broker.open_order("BTCUSD", "buy", 1.0)
    broker.set_price("BTCUSD", 40100.0)
    info = broker.account_info()
    # 100 move * 1.0 = +100
    assert info.equity == 10100.0


def test_loss_on_price_move(broker):
    order = broker.open_order("BTCUSD", "buy", 1.0)
    broker.set_price("BTCUSD", 39900.0)
    info = broker.account_info()
    assert info.equity == 9900.0
