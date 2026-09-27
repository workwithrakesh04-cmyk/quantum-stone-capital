"""Tests for PropRuleEngine."""
import pytest
from core.prop_rules import PropRuleEngine, PropRuleResult
from brokers.sim_broker import AccountState


@pytest.fixture
def account():
    return AccountState(
        name="prop",
        account_type="prop_firm",
        starting_balance=100000.0,
        balance=100000.0,
        equity=100000.0,
        peak_equity=100000.0,
    )


@pytest.fixture
def engine():
    return PropRuleEngine()


def test_ok_when_within_limits(engine, account):
    r = engine.evaluate(account, risk_amount=500.0)
    assert r.allowed
    assert r.reason == "OK"


def test_rejects_risk_exceeds_limit(engine, account):
    # 1% of 100k = 1000; try 2000
    r = engine.evaluate(account, risk_amount=2000.0)
    assert not r.allowed
    assert "risk_exceeds_limit" in r.reason


def test_rejects_daily_loss_hit(engine, account):
    account.daily_pnl = -6000.0  # -6% (exceeds 5%)
    r = engine.evaluate(account, risk_amount=500.0)
    assert not r.allowed
    assert "daily_loss_limit_hit" in r.reason


def test_rejects_drawdown_hit(engine, account):
    account.peak_equity = 100000.0
    account.equity = 89000.0  # -11% DD
    r = engine.evaluate(account, risk_amount=500.0)
    assert not r.allowed
    assert "max_drawdown_hit" in r.reason


def test_rejects_max_positions(engine, account):
    from brokers.sim_broker import Position
    for i in range(5):
        account.positions.append(Position(
            ticket=i, symbol="BTCUSD", side="buy", volume=0.01, entry_price=40000.0,
        ))
    r = engine.evaluate(account, risk_amount=500.0)
    assert not r.allowed
    assert "max_positions_reached" in r.reason


def test_rejects_weekend_holding(engine, account):
    r = engine.evaluate(account, risk_amount=500.0, is_weekend=True)
    assert not r.allowed
    assert r.reason == "weekend_holding_not_allowed"


def test_allows_news_trading(engine, account):
    r = engine.evaluate(account, risk_amount=500.0, is_news_time=True)
    assert r.allowed
    assert "news_time" in r.warnings


def test_warns_approaching_daily_loss(engine, account):
    account.daily_pnl = -4000.0  # -4% (70% of 5% limit)
    r = engine.evaluate(account, risk_amount=500.0)
    assert r.allowed
    assert "approaching_daily_loss" in r.warnings


def test_warns_approaching_max_drawdown(engine, account):
    account.peak_equity = 100000.0
    account.equity = 92000.0  # -8% DD (80% of 10%)
    r = engine.evaluate(account, risk_amount=500.0)
    assert r.allowed
    assert "approaching_max_drawdown" in r.warnings


def test_no_consistency_rule_applied(engine, account):
    # Even with 100% of profit on day 1, still allowed
    account.daily_pnl = 8000.0
    r = engine.evaluate(account, risk_amount=500.0)
    assert r.allowed


def test_risk_exactly_at_limit(engine, account):
    # 1% of 100k = 1000 exactly
    r = engine.evaluate(account, risk_amount=1000.0)
    assert r.allowed


def test_risk_one_over_limit(engine, account):
    r = engine.evaluate(account, risk_amount=1000.01)
    assert not r.allowed


def test_daily_loss_exactly_at_limit(engine, account):
    account.daily_pnl = -5000.0  # exactly 5%
    r = engine.evaluate(account, risk_amount=500.0)
    assert not r.allowed


def test_drawdown_exactly_at_limit(engine, account):
    account.peak_equity = 100000.0
    account.equity = 90000.0  # exactly 10%
    r = engine.evaluate(account, risk_amount=500.0)
    assert not r.allowed


def test_default_config_values(engine):
    assert engine.max_risk_per_trade == 0.01
    assert engine.max_daily_loss == 0.05
    assert engine.max_drawdown == 0.10
    assert engine.allow_weekend_holding is False
    assert engine.allow_news_trading is True
    assert engine.max_concurrent_positions == 5
