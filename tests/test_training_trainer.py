"""Tests for training.trainer."""
import json
import pytest
from pathlib import Path

from training.trainer import Trainer
from consensus.audit import ConsensusAudit


@pytest.fixture
def setup(tmp_path):
    audit = ConsensusAudit(
        log_dir=str(tmp_path / "consensus"),
        archive_dir=str(tmp_path / "consensus" / "archive"),
    )
    state_dir = str(tmp_path / "models")
    pointer = str(tmp_path / "models" / "current.json")
    trainer = Trainer(audit=audit, state_dir=state_dir, pointer_file=pointer)
    return audit, trainer, tmp_path


def test_no_op_day_writes_folder(setup):
    audit, trainer, tmp = setup
    report = trainer.train(day="2026-01-01")
    assert report["no_op"] is True
    assert Path(report["state_folder"]).exists()


def test_training_writes_required_files(setup):
    audit, trainer, tmp = setup
    day = audit._utc_day()
    audit.write({"outcome": "WIN", "beta": {"contributing_strategies": ["foo"], "regime": "RANGING"}})
    report = trainer.train(day=day)
    folder = Path(report["state_folder"])
    assert (folder / "strategy_weights.json").exists()
    assert (folder / "arbiter_thresholds.json").exists()
    assert (folder / "training_report.json").exists()
    assert (folder / "meta.json").exists()


def test_pointer_updated(setup):
    audit, trainer, tmp = setup
    day = audit._utc_day()
    audit.write({"outcome": "WIN"})
    trainer.train(day=day)
    pointer = Path(trainer.pointer_file)
    assert pointer.exists()
    data = json.loads(pointer.read_text(encoding="utf-8"))
    assert data["active"] == day


def test_previous_weights_loaded(setup):
    audit, trainer, tmp = setup
    day1 = "2026-01-01"
    audit.write({"outcome": "WIN", "beta": {"contributing_strategies": ["foo"], "regime": "RANGING"}})
    trainer.train(day=day1)
    weights_path = Path(trainer.state_dir) / day1 / "strategy_weights.json"
    w1 = json.loads(weights_path.read_text(encoding="utf-8"))
    # Second day should load previous
    day2 = "2026-01-02"
    trainer.train(day=day2)
    weights_path2 = Path(trainer.state_dir) / day2 / "strategy_weights.json"
    w2 = json.loads(weights_path2.read_text(encoding="utf-8"))
    assert w1 == w2  # no new samples, weights preserved


def test_archive_skipped_on_no_op(setup):
    audit, trainer, tmp = setup
    day = audit._utc_day()
    audit.write({"outcome": None})  # no outcome
    report = trainer.train(day=day)
    assert report["no_op"] is True
    # Not archived because no_op
    active_file = audit.log_dir / f"{day}.jsonl"
    assert active_file.exists()


def test_archive_runs_on_real_training(setup):
    audit, trainer, tmp = setup
    day = audit._utc_day()
    audit.write({"outcome": "WIN", "beta": {"contributing_strategies": ["foo"], "regime": "RANGING"}})
    report = trainer.train(day=day)
    assert report["no_op"] is False
    assert report["archived"] is not None


def test_report_fields(setup):
    audit, trainer, tmp = setup
    report = trainer.train(day="2026-01-01")
    assert "day" in report
    assert "samples" in report
    assert "samples_with_outcome" in report
    assert "no_op" in report
    assert "state_folder" in report


def test_train_uses_utc_day_default(setup):
    audit, trainer, tmp = setup
    report = trainer.train()
    assert report["day"] == audit._utc_day()
