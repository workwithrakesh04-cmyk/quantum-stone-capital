"""Tests for training.loader."""
import pytest

from training.loader import TrainingLoader, TrainingSample
from consensus.audit import ConsensusAudit


@pytest.fixture
def sample_audit(tmp_path):
    return ConsensusAudit(
        log_dir=str(tmp_path / "c"),
        archive_dir=str(tmp_path / "c" / "a"),
    )


def test_sample_normalize_buy_to_long():
    s = TrainingSample({"qsc": {"direction": "long"}, "beta": {"direction": "BUY"}})
    assert s.qsc_direction == "LONG"
    assert s.beta_direction == "LONG"


def test_sample_normalize_sell_to_short():
    s = TrainingSample({"qsc": {"direction": "short"}, "beta": {"direction": "SELL"}})
    assert s.qsc_direction == "SHORT"
    assert s.beta_direction == "SHORT"


def test_sample_hold_normalization():
    s = TrainingSample({"qsc": {"direction": "flat"}, "beta": {"direction": "HOLD"}})
    assert s.qsc_direction == "HOLD"
    assert s.beta_direction == "HOLD"


def test_sample_has_outcome_win():
    s = TrainingSample({"outcome": "WIN"})
    assert s.has_outcome() is True


def test_sample_has_outcome_missing():
    s = TrainingSample({})
    assert s.has_outcome() is False


def test_loader_load_day_empty(sample_audit):
    loader = TrainingLoader(audit=sample_audit)
    samples = loader.load_day("1999-01-01")
    assert samples == []


def test_loader_filters_with_outcome(sample_audit):
    day = sample_audit._utc_day()
    sample_audit.write({"outcome": "WIN", "pnl_usd": 10})
    sample_audit.write({"outcome": None, "pnl_usd": 0})
    sample_audit.write({"outcome": "LOSS", "pnl_usd": -5})
    loader = TrainingLoader(audit=sample_audit)
    samples = loader.load_day(day)
    filtered = loader.filter_with_outcome(samples)
    assert len(filtered) == 2


def test_loader_groups_by_consensus(sample_audit):
    day = sample_audit._utc_day()
    sample_audit.write({"arbiter": {"consensus": "BOTH_AGREE"}})
    sample_audit.write({"arbiter": {"consensus": "BOTH_AGREE"}})
    sample_audit.write({"arbiter": {"consensus": "DISAGREE"}})
    loader = TrainingLoader(audit=sample_audit)
    samples = loader.load_day(day)
    grouped = loader.group_by_consensus(samples)
    assert len(grouped["BOTH_AGREE"]) == 2
    assert len(grouped["DISAGREE"]) == 1


def test_loader_stats(sample_audit):
    day = sample_audit._utc_day()
    sample_audit.write({"outcome": "WIN"})
    sample_audit.write({"outcome": None})
    loader = TrainingLoader(audit=sample_audit)
    samples = loader.load_day(day)
    stats = loader.stats(samples)
    assert stats["total"] == 2
    assert stats["with_outcome"] == 1
