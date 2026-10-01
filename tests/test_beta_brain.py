"""Tests for beta_brain.beta_brain."""
from beta_brain.beta_brain import BetaBrain


class FakeContext:
    def __init__(self, closes, highs=None, lows=None, opens=None, volumes=None):
        self.symbol = "BTCUSD"
        self.timeframe = "5m"
        self.closes = closes
        self.highs = highs if highs is not None else [c * 1.005 for c in closes]
        self.lows = lows if lows is not None else [c * 0.995 for c in closes]
        self.opens = opens if opens is not None else list(closes)
        self.volumes = volumes if volumes is not None else [1.0] * len(closes)
        self.momentum = None
        self.regime = "RANGING"


def test_beta_brain_initializes():
    bb = BetaBrain()
    status = bb.get_status()
    assert status["timeframe"] == "5m"
    assert status["registry"]["active"] >= 0


def test_beta_brain_context_to_candles():
    bb = BetaBrain()
    ctx = FakeContext([100.0, 101.0, 102.0])
    candles = bb._context_to_candles(ctx)
    assert len(candles) == 3
    assert candles[0]["close"] == 100.0
    assert candles[-1]["close"] == 102.0


def test_beta_brain_returns_none_on_empty_context():
    bb = BetaBrain()
    ctx = FakeContext([])
    verdict = bb.run(ctx)
    assert verdict is None


def test_beta_brain_returns_none_on_short_history():
    bb = BetaBrain()
    ctx = FakeContext([100.0] * 20)
    verdict = bb.run(ctx)
    assert verdict is None


def test_beta_brain_runs_without_raising():
    bb = BetaBrain()
    ctx = FakeContext([100.0 + i * 0.1 for i in range(150)])
    bb.run(ctx)


def test_beta_brain_status_fields():
    bb = BetaBrain()
    status = bb.get_status()
    assert "registry" in status
    assert "active" in status["registry"]
    assert "shadow" in status["registry"]


def test_beta_brain_handles_missing_configs():
    bb = BetaBrain(
        personal_config_path="nonexistent.yaml",
        prop_config_path="nonexistent.yaml",
    )
    assert bb is not None


def test_beta_brain_silent_on_errors():
    bb = BetaBrain()

    class BadContext:
        symbol = "BTCUSD"
        timeframe = "5m"
        closes = "not a list"
        highs = None
        lows = None
        opens = None
        volumes = None
        momentum = None
        regime = None

    result = bb.run(BadContext())
    assert result is None
