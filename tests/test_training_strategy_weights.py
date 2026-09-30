"""Tests for training.strategy_weights."""
from training.strategy_weights import StrategyWeightTrainer
from training.loader import TrainingSample


def _sample(strategies, outcome, pnl=10.0, regime="RANGING"):
    return TrainingSample({
        "beta": {"contributing_strategies": strategies, "regime": regime},
        "outcome": outcome,
        "pnl_usd": pnl,
    })


def test_empty_samples_returns_previous():
    t = StrategyWeightTrainer()
    w = t.compute([], previous_weights={"foo": 1.2})
    assert w["foo"] == 1.2


def test_insufficient_data_keeps_previous():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "WIN")]  # only 1 trade, need 3
    w = t.compute(samples, previous_weights={"foo": 1.2})
    assert w["foo"] == 1.2


def test_high_win_rate_increases_weight():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "WIN") for _ in range(5)]
    w = t.compute(samples, previous_weights={"foo": 1.0})
    assert w["foo"] > 1.0
    assert w["foo"] <= 1.5


def test_low_win_rate_decreases_weight():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "LOSS") for _ in range(5)]
    w = t.compute(samples, previous_weights={"foo": 1.0})
    assert w["foo"] < 1.0
    assert w["foo"] >= 0.5


def test_weight_capped_at_max():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "WIN") for _ in range(20)]
    w = t.compute(samples, previous_weights={"foo": 1.4})
    assert w["foo"] <= 1.5


def test_weight_capped_at_min():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "LOSS") for _ in range(20)]
    w = t.compute(samples, previous_weights={"foo": 0.6})
    assert w["foo"] >= 0.5


def test_default_weight_is_one():
    t = StrategyWeightTrainer()
    samples = [_sample(["newstrat"], "WIN") for _ in range(5)]
    w = t.compute(samples, previous_weights={})
    assert "newstrat" in w
    assert w["newstrat"] > 1.0


def test_report_counts_changes():
    t = StrategyWeightTrainer()
    samples = [_sample(["foo"], "WIN") for _ in range(5)]
    w = t.compute(samples, previous_weights={"foo": 1.0})
    report = t.report(samples, w, prev={"foo": 1.0})
    assert report["n_strategies_updated"] == 1
