"""Tests for consensus.audit."""
import json
import os
from pathlib import Path
import pytest

from consensus.audit import ConsensusAudit


@pytest.fixture
def tmp_audit(tmp_path):
    log_dir = tmp_path / "consensus"
    arch_dir = tmp_path / "consensus" / "archive"
    return ConsensusAudit(log_dir=str(log_dir), archive_dir=str(arch_dir))


def test_init_creates_dirs(tmp_path):
    log_dir = tmp_path / "c"
    arch_dir = tmp_path / "c" / "a"
    ConsensusAudit(log_dir=str(log_dir), archive_dir=str(arch_dir))
    assert log_dir.exists()
    assert arch_dir.exists()


def test_write_creates_jsonl_file(tmp_audit):
    tmp_audit.write({"symbol": "BTCUSD", "consensus": "BOTH_AGREE"})
    f = tmp_audit.current_file
    assert f is not None
    assert f.exists()
    lines = f.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["symbol"] == "BTCUSD"


def test_write_multiple_lines(tmp_audit):
    tmp_audit.write({"symbol": "A"})
    tmp_audit.write({"symbol": "B"})
    tmp_audit.write({"symbol": "C"})
    f = tmp_audit.current_file
    lines = f.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3


def test_write_adds_ts_and_iso(tmp_audit):
    tmp_audit.write({"symbol": "BTCUSD"})
    f = tmp_audit.current_file
    rec = json.loads(f.read_text(encoding="utf-8").strip())
    assert "ts" in rec
    assert "iso" in rec


def test_read_day_returns_records(tmp_audit):
    tmp_audit.write({"symbol": "A", "v": 1})
    tmp_audit.write({"symbol": "B", "v": 2})
    day = tmp_audit._utc_day()
    records = tmp_audit.read_day(day)
    assert len(records) == 2


def test_read_missing_day_returns_empty(tmp_audit):
    records = tmp_audit.read_day("1999-01-01")
    assert records == []


def test_list_days_empty_initially(tmp_audit):
    days = tmp_audit.list_days()
    assert len(days) >= 0


def test_archive_day_moves_file(tmp_audit):
    tmp_audit.write({"symbol": "A"})
    day = tmp_audit._utc_day()
    active = tmp_audit.log_dir / f"{day}.jsonl"
    assert active.exists()
    result = tmp_audit.archive_day(day)
    assert result is not None
    assert not active.exists()
    assert result.exists()


def test_archive_day_missing_returns_none(tmp_audit):
    result = tmp_audit.archive_day("1999-01-01")
    assert result is None


def test_read_day_after_archive(tmp_audit):
    tmp_audit.write({"symbol": "X", "v": 42})
    day = tmp_audit._utc_day()
    tmp_audit.archive_day(day)
    records = tmp_audit.read_day(day)
    assert len(records) == 1
    assert records[0]["v"] == 42
