"""Tests for beta_brain.jury.transcript."""
import json
from beta_brain.jury.transcript import RiskVerdict, PortfolioVerdict, JuryVerdict


def test_risk_verdict_to_dict():
    r = RiskVerdict(approved=True, mode="scalp", position_size_qty=1.5)
    d = r.to_dict()
    assert d["approved"] is True
    assert d["mode"] == "scalp"
    assert d["position_size_qty"] == 1.5


def test_portfolio_verdict_defaults():
    p = PortfolioVerdict(approved=True)
    assert p.current_open_positions == 0
    assert p.notes == []


def test_jury_verdict_to_dict():
    r = RiskVerdict(approved=True, mode="scalp")
    p = PortfolioVerdict(approved=True)
    jv = JuryVerdict(
        ts=1, symbol="BTCUSD", mode="scalp",
        debate_winner="BUY", debate_confidence=0.7,
        risk=r, portfolio=p, final_decision="APPROVED",
    )
    d = jv.to_dict()
    assert d["final_decision"] == "APPROVED"
    assert d["debate_winner"] == "BUY"
    assert "risk" in d
    assert "portfolio" in d


def test_jury_verdict_to_json_roundtrip():
    r = RiskVerdict(approved=True, mode="scalp")
    p = PortfolioVerdict(approved=True)
    jv = JuryVerdict(
        ts=1, symbol="X", mode="scalp",
        debate_winner="SELL", debate_confidence=0.6,
        risk=r, portfolio=p, final_decision="APPROVED",
    )
    raw = jv.to_json()
    parsed = json.loads(raw)
    assert parsed["debate_winner"] == "SELL"


def test_jury_verdict_optional_fields_defaults():
    r = RiskVerdict(approved=True, mode="scalp")
    p = PortfolioVerdict(approved=True)
    jv = JuryVerdict(
        ts=1, symbol="X", mode="scalp",
        debate_winner="BUY", debate_confidence=0.5,
        risk=r, portfolio=p, final_decision="APPROVED",
    )
    assert jv.account_type == "personal"
    assert jv.final_reason == ""
