"""Tests for beta_brain.debate.transcript."""
import json
from beta_brain.debate.transcript import Argument, DebateTranscript


def test_argument_to_dict():
    a = Argument(bot="BUY", round=1, confidence=0.5, statement="x")
    d = a.to_dict()
    assert d["bot"] == "BUY"
    assert d["round"] == 1
    assert d["evidence"] == []


def test_argument_rebuttals():
    a = Argument(bot="SELL", round=2, confidence=0.6, statement="y", rebuttals=["r1"])
    assert a.rebuttals == ["r1"]


def test_transcript_to_dict():
    t = DebateTranscript(
        ts=1, symbol="BTCUSD", timeframe="5m", signals_input=[],
        rounds=[[], [], []], winner="BUY", winner_confidence=0.7,
        final_scores={"BUY": 0.7, "SELL": 0.2, "HOLD": 0.1},
    )
    d = t.to_dict()
    assert d["winner"] == "BUY"
    assert d["final_scores"]["BUY"] == 0.7


def test_transcript_to_json_roundtrip():
    t = DebateTranscript(
        ts=1, symbol="X", timeframe="5m", signals_input=[{"s": 1}],
        rounds=[[], [], []], winner="HOLD", winner_confidence=0.5,
        final_scores={"BUY": 0.1, "SELL": 0.1, "HOLD": 0.5},
    )
    raw = t.to_json()
    parsed = json.loads(raw)
    assert parsed["winner"] == "HOLD"
    assert parsed["signals_input"] == [{"s": 1}]
