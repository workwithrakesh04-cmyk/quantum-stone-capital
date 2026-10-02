"""D8 tests - ShadowAudit JSONL writer."""
import json
import os
import tempfile
from pathlib import Path

import pytest

from beta_brain.shadow_audit import ShadowAudit


@pytest.fixture
def tmp_audit():
    with tempfile.TemporaryDirectory() as td:
        log_dir = os.path.join(td, "shadow")
        archive = os.path.join(td, "shadow", "archive")
        yield ShadowAudit(log_dir=log_dir, archive_dir=archive), log_dir


class TestWriteAndRead:

    def test_write_creates_file(self, tmp_audit):
        audit, log_dir = tmp_audit
        audit.write({"kind": "verdict", "x": 1})
        files = list(Path(log_dir).glob("*.jsonl"))
        assert len(files) == 1

    def test_write_then_read_roundtrip(self, tmp_audit):
        audit, _ = tmp_audit
        audit.write({"kind": "verdict", "value": 42})
        audit.write({"kind": "trade_open", "value": 43})
        day = audit._utc_day()
        records = audit.read_day(day)
        assert len(records) == 2
        assert records[0]["kind"] == "verdict"
        assert records[0]["value"] == 42
        assert records[1]["value"] == 43

    def test_ts_and_iso_auto_added(self, tmp_audit):
        audit, _ = tmp_audit
        audit.write({"kind": "x"})
        day = audit._utc_day()
        records = audit.read_day(day)
        assert "ts" in records[0]
        assert "iso" in records[0]

    def test_explicit_ts_not_overwritten(self, tmp_audit):
        audit, _ = tmp_audit
        audit.write({"kind": "x", "ts": 12345, "iso": "custom"})
        records = audit.read_day(audit._utc_day())
        assert records[0]["ts"] == 12345
        assert records[0]["iso"] == "custom"

    def test_write_many_returns_count(self, tmp_audit):
        audit, _ = tmp_audit
        n = audit.write_many([{"a": 1}, {"a": 2}, {"a": 3}])
        assert n == 3

    def test_read_missing_day_returns_empty(self, tmp_audit):
        audit, _ = tmp_audit
        assert audit.read_day("1999-01-01") == []


class TestListAndNewest:

    def test_list_days_empty(self, tmp_audit):
        audit, _ = tmp_audit
        # Before any writes, an empty file was created for today.
        # list_days should show today.
        days = audit.list_days()
        assert isinstance(days, list)

    def test_list_days_after_write(self, tmp_audit):
        audit, _ = tmp_audit
        audit.write({"kind": "x"})
        days = audit.list_days()
        assert audit._utc_day() in days

    def test_newest_active_day_none_when_empty(self, tmp_audit):
        audit, _ = tmp_audit
        # The active file exists but is 0 bytes -> newest_active_day
        # with min_size=1 should return None.
        assert audit.newest_active_day(min_size=1) is None

    def test_newest_active_day_after_write(self, tmp_audit):
        audit, _ = tmp_audit
        audit.write({"kind": "x"})
        newest = audit.newest_active_day(min_size=1)
        assert newest == audit._utc_day()


class TestArchive:

    def test_archive_moves_file(self, tmp_audit):
        audit, log_dir = tmp_audit
        day = audit._utc_day()
        audit.write({"kind": "x"})
        moved = audit.archive_day(day)
        assert moved is not None
        assert Path(moved).exists()
        # Original is gone from active dir
        assert not (Path(log_dir) / f"{day}.jsonl").exists()
        # But read_day still finds it via archive
        records = audit.read_day(day)
        assert len(records) == 1

    def test_archive_missing_day_returns_none(self, tmp_audit):
        audit, _ = tmp_audit
        assert audit.archive_day("1999-01-01") is None


class TestEncodingTolerance:

    def test_utf8_sig_reader(self, tmp_audit):
        audit, log_dir = tmp_audit
        day = audit._utc_day()
        path = Path(log_dir) / f"{day}.jsonl"
        # Overwrite with UTF-8 BOM content
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(json.dumps({"kind": "bom"}) + "\n")
        records = audit.read_day(day)
        assert len(records) == 1
        assert records[0]["kind"] == "bom"

    def test_skips_malformed_line(self, tmp_audit):
        audit, log_dir = tmp_audit
        day = audit._utc_day()
        path = Path(log_dir) / f"{day}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "good1"}) + "\n")
            f.write("not valid json\n")
            f.write(json.dumps({"kind": "good2"}) + "\n")
        records = audit.read_day(day)
        assert len(records) == 2
        assert records[0]["kind"] == "good1"
        assert records[1]["kind"] == "good2"