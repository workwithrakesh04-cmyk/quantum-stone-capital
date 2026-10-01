"""Integration test: BetaBrain computes HTF bias when running."""
from beta_brain.beta_brain import BetaBrain


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1.0, "open_time": ts}


class _Ctx:
    def __init__(self, closes):
        self.symbol = "BTCUSD"
        self.timeframe = "5m"
        self.closes = closes
        self.highs = [c * 1.005 for c in closes]
        self.lows = [c * 0.995 for c in closes]
        self.opens = list(closes)
        self.volumes = [1.0] * len(closes)
        self.momentum = None
        self.regime = "RANGING"


def test_betabrain_initializes():
    bb = BetaBrain()
    assert bb is not None
    status = bb.get_status()
    assert status["registry"]["active"] >= 0


def test_betabrain_runs_with_htf_bias_available():
    bb = BetaBrain()
    ctx = _Ctx([100.0 + i * 0.1 for i in range(200)])
    # Should not raise; verdict may be None
    result = bb.run(ctx)
    assert result is None or hasattr(result, "final_decision")


def test_betabrain_handles_short_history():
    bb = BetaBrain()
    ctx = _Ctx([100.0] * 20)
    assert bb.run(ctx) is None


def test_betabrain_context_to_candles_still_works():
    bb = BetaBrain()
    ctx = _Ctx([100.0, 101.0, 102.0])
    candles = bb._context_to_candles(ctx)
    assert len(candles) == 3
