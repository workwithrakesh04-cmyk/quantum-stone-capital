"""Tests for beta_brain.strategy_analyzer."""
from beta_brain.strategy_analyzer import StrategyAnalyzer


def test_empty_analyzer():
    a = StrategyAnalyzer()
    d = a.to_dict()
    assert d["strategies"] == {}


def test_record_single_win():
    a = StrategyAnalyzer()
    a.record_trade(["foo"], "LONG", 100.0, "RANGING")
    d = a.to_dict()
    assert d["strategies"]["foo"]["trades"] == 1
    assert d["strategies"]["foo"]["wins"] == 1
    assert d["strategies"]["foo"]["net_pnl"] == 100.0


def test_record_single_loss():
    a = StrategyAnalyzer()
    a.record_trade(["foo"], "LONG", -50.0, "RANGING")
    d = a.to_dict()
    assert d["strategies"]["foo"]["losses"] == 1
    assert d["strategies"]["foo"]["net_pnl"] == -50.0


def test_pnl_split_across_strategies():
    a = StrategyAnalyzer()
    a.record_trade(["foo", "bar"], "LONG", 100.0, "RANGING")
    d = a.to_dict()
    assert d["strategies"]["foo"]["net_pnl"] == 50.0
    assert d["strategies"]["bar"]["net_pnl"] == 50.0


def test_empty_strategies_ignored():
    a = StrategyAnalyzer()
    a.record_trade([], "LONG", 100.0, "RANGING")
    d = a.to_dict()
    assert d["strategies"] == {}


def test_regime_attribution():
    a = StrategyAnalyzer()
    a.record_trade(["foo"], "LONG", 100.0, "TRENDING_UP")
    d = a.to_dict()
    assert "TRENDING_UP" in d["regimes"]
    assert d["regimes"]["TRENDING_UP"]["foo"]["trades"] == 1


def test_direction_attribution():
    a = StrategyAnalyzer()
    a.record_trade(["foo"], "LONG", 100.0, "RANGING")
    a.record_trade(["foo"], "SHORT", -50.0, "RANGING")
    d = a.to_dict()
    assert d["directions"]["LONG"]["foo"]["trades"] == 1
    assert d["directions"]["SHORT"]["foo"]["trades"] == 1


def test_win_rate_calculation():
    a = StrategyAnalyzer()
    a.record_trade(["foo"], "LONG", 100.0, "RANGING")
    a.record_trade(["foo"], "LONG", 100.0, "RANGING")
    a.record_trade(["foo"], "LONG", -50.0, "RANGING")
    d = a.to_dict()
    assert d["strategies"]["foo"]["win_rate"] == pytest.approx(66.67, abs=0.1)


import pytest  # noqa: E402
