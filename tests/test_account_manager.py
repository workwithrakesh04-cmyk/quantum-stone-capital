"""Tests for AccountManager."""
import pytest
from core.account_manager import AccountManager


@pytest.fixture
def manager():
    return AccountManager("config/master.yaml")


def test_init(manager):
    assert "personal" in manager.accounts
    assert "prop" in manager.accounts
    assert manager.accounts["personal"].capital == 10000


def test_can_open_trade_ok(manager):
    allowed, reason = manager.can_open_trade("personal", risk_amount=50, instrument="BTCUSD")
    assert allowed, reason


def test_can_open_trade_rejects_wrong_instrument(manager):
    allowed, reason = manager.can_open_trade("personal", risk_amount=50, instrument="DOGEUSD")
    assert not allowed
    assert "not in allowed instruments" in reason


def test_can_open_trade_rejects_oversized_risk(manager):
    allowed, reason = manager.can_open_trade("personal", risk_amount=500, instrument="BTCUSD")
    assert not allowed
    assert "Risk" in reason
