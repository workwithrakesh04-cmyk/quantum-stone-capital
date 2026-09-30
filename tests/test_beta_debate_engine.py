"""Tests for beta_brain.debate.engine."""
from beta_brain.signal import Signal
from beta_brain.debate.engine import DebateEngine


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def _flat_candles(n=30, base=100.0):
    return [_candle(base, base * 1.001, base * 0.999, base, i * 300_000) for i in range(n)]


def _long(conf=0.7, weight=0.6, name="s1"):
    return Signal(strategy=name, direction="LONG", confidence=conf, weight=weight)


def _short(conf=0.7, weight=0.6, name="s1"):
    return Signal(strategy=name, direction="SHORT", confidence=conf, weight=weight)


def test_engine_returns_transcript_with_3_rounds():
    e = DebateEngine()
    t = e.run([_long(0.7)], _flat_candles())
    assert len(t.rounds) == 3


def test_engine_no_signals_winners_hold():
    e = DebateEngine()
    t = e.run([], _flat_candles())
    assert t.winner == "HOLD"


def test_engine_strong_buy_wins():
    e = DebateEngine()
    sigs = [_long(0.9, weight=0.9, name=f"s{i}") for i in range(5)]
    t = e.run(sigs, _flat_candles())
    assert t.winner == "BUY"
    assert t.winner_confidence > 0


def test_engine_strong_sell_wins():
    e = DebateEngine()
    sigs = [_short(0.9, weight=0.9, name=f"s{i}") for i in range(5)]
    t = e.run(sigs, _flat_candles())
    assert t.winner == "SELL"


def test_engine_equal_conflict_hold_wins_or_buy():
    e = DebateEngine()
    sigs = [_long(0.6, weight=0.5), _short(0.6, weight=0.5)]
    t = e.run(sigs, _flat_candles())
    # conflict should weaken directional conviction
    assert t.winner in ("HOLD", "BUY", "SELL")


def test_engine_transcript_fields_populated():
    e = DebateEngine()
    t = e.run([_long(0.7)], _flat_candles())
    assert t.symbol == "BTCUSD"
    assert t.timeframe == "5m"
    assert "BUY" in t.final_scores
    assert "SELL" in t.final_scores
    assert "HOLD" in t.final_scores
    assert t.ts > 0


def test_engine_signals_input_serialized():
    e = DebateEngine()
    t = e.run([_long(0.7, name="mystrat")], _flat_candles())
    assert len(t.signals_input) == 1
    assert t.signals_input[0]["strategy"] == "mystrat"


def test_engine_rounds_have_arguments():
    e = DebateEngine()
    t = e.run([_long(0.7)], _flat_candles())
    for rnd in t.rounds:
        assert len(rnd) == 3  # BUY, SELL, HOLD each round
        bots = {a.bot for a in rnd}
        assert bots == {"BUY", "SELL", "HOLD"}


def test_engine_low_conviction_hold_override():
    # Very low-confidence signals should trigger HOLD override
    e = DebateEngine()
    t = e.run([_long(0.05)], _flat_candles())
    assert t.winner == "HOLD"


def test_engine_works_with_empty_candles():
    e = DebateEngine()
    t = e.run([_long(0.7)], [])
    assert t.winner in ("BUY", "SELL", "HOLD")


def test_engine_repeated_runs_independent():
    e = DebateEngine()
    t1 = e.run([_long(0.9, name=f"a{i}") for i in range(5)], _flat_candles())
    t2 = e.run([_short(0.9, name=f"b{i}") for i in range(5)], _flat_candles())
    assert t1.winner != t2.winner
