"""Tests for beta_brain.jury.final_jury."""
from beta_brain.jury.final_jury import FinalJury
from beta_brain.jury.transcript import RiskVerdict, PortfolioVerdict
from beta_brain.debate.transcript import DebateTranscript


def _debate():
    return DebateTranscript(
        ts=1, symbol="BTCUSD", timeframe="5m", signals_input=[],
        rounds=[[], [], []], winner="BUY", winner_confidence=0.7,
        final_scores={"BUY": 0.7, "SELL": 0.1, "HOLD": 0.2},
    )


def test_both_approved():
    fj = FinalJury()
    r = RiskVerdict(approved=True, mode="scalp", position_size_qty=1)
    p = PortfolioVerdict(approved=True)
    v = fj.evaluate(_debate(), r, p)
    assert v.final_decision == "APPROVED"


def test_risk_rejected():
    fj = FinalJury()
    r = RiskVerdict(approved=False, mode="scalp", reject_reason="test")
    p = PortfolioVerdict(approved=True)
    v = fj.evaluate(_debate(), r, p)
    assert v.final_decision == "REJECTED"
    assert "risk" in v.final_reason


def test_portfolio_rejected():
    fj = FinalJury()
    r = RiskVerdict(approved=True, mode="scalp")
    p = PortfolioVerdict(approved=False, reject_reason="too many")
    v = fj.evaluate(_debate(), r, p)
    assert v.final_decision == "REJECTED"
    assert "portfolio" in v.final_reason


def test_both_rejected():
    fj = FinalJury()
    r = RiskVerdict(approved=False, mode="scalp", reject_reason="r")
    p = PortfolioVerdict(approved=False, reject_reason="p")
    v = fj.evaluate(_debate(), r, p)
    assert v.final_decision == "REJECTED"
    assert "risk" in v.final_reason
    assert "portfolio" in v.final_reason
