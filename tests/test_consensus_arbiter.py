"""Tests for consensus.arbiter."""
from dataclasses import dataclass, field
from consensus.arbiter import ConsensusArbiter, ArbiterDecision


@dataclass
class FakeQSCResult:
    decision: str = "trade"
    direction: str = "long"
    confidence: float = 0.7
    metadata: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    strategy_name: str = "ict_bos"
    warnings: list = field(default_factory=list)


@dataclass
class FakeRisk:
    notes: list = field(default_factory=list)


@dataclass
class FakeVerdict:
    final_decision: str = "APPROVED"
    debate_winner: str = "BUY"
    debate_confidence: float = 0.7
    risk: FakeRisk = field(default_factory=FakeRisk)


def test_arbiter_initializes():
    a = ConsensusArbiter()
    assert a.size_multiplier["BOTH_AGREE"] == 1.0


def test_both_agree_full_size():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="long"), FakeVerdict(debate_winner="BUY"))
    assert d.consensus == "BOTH_AGREE"
    assert d.direction == "LONG"
    assert d.size_multiplier == 1.0


def test_both_agree_short():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="short"), FakeVerdict(debate_winner="SELL"))
    assert d.consensus == "BOTH_AGREE"
    assert d.direction == "SHORT"
    assert d.size_multiplier == 1.0


def test_qsc_only_half_size():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="long"), None)
    assert d.consensus == "QSC_ONLY"
    assert d.direction == "LONG"
    assert d.size_multiplier == 0.5


def test_beta_only_half_size():
    a = ConsensusArbiter()
    qsc = FakeQSCResult(decision="no_trade", direction="flat")
    d = a.decide(qsc, FakeVerdict(debate_winner="BUY"))
    assert d.consensus == "BETA_ONLY"
    assert d.direction == "LONG"
    assert d.size_multiplier == 0.5


def test_disagree_no_trade():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="long"), FakeVerdict(debate_winner="SELL"))
    assert d.consensus == "DISAGREE"
    assert d.direction == "HOLD"
    assert d.size_multiplier == 0.0


def test_both_hold_no_trade():
    a = ConsensusArbiter()
    qsc = FakeQSCResult(decision="no_trade", direction="flat")
    d = a.decide(qsc, None)
    assert d.consensus == "BOTH_HOLD"
    assert d.direction == "HOLD"
    assert d.size_multiplier == 0.0


def test_rejected_beta_verdict_treated_as_hold():
    a = ConsensusArbiter()
    qsc = FakeQSCResult(decision="no_trade", direction="flat")
    d = a.decide(qsc, FakeVerdict(final_decision="REJECTED", debate_winner="BUY"))
    assert d.consensus == "BOTH_HOLD"


def test_to_dict_roundtrip():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="long"), FakeVerdict(debate_winner="BUY"))
    dd = d.to_dict()
    assert dd["consensus"] == "BOTH_AGREE"
    assert dd["size_multiplier"] == 1.0


def test_is_trade_property():
    a = ConsensusArbiter()
    d = a.decide(FakeQSCResult(direction="long"), FakeVerdict(debate_winner="BUY"))
    assert d.is_trade is True
    d2 = a.decide(FakeQSCResult(decision="no_trade", direction="flat"), None)
    assert d2.is_trade is False


def test_never_raises_on_bad_input():
    a = ConsensusArbiter()
    d = a.decide(None, None)
    assert d.consensus == "BOTH_HOLD"


def test_beta_only_short():
    a = ConsensusArbiter()
    qsc = FakeQSCResult(decision="no_trade", direction="flat")
    d = a.decide(qsc, FakeVerdict(debate_winner="SELL"))
    assert d.consensus == "BETA_ONLY"
    assert d.direction == "SHORT"
