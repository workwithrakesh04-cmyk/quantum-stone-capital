"""Consensus Audit - writes each Arbiter decision to JSONL,
rotates at day boundary, archives to logs/consensus/archive/.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


class ConsensusAudit:
    def __init__(
        self,
        log_dir: str = "logs/consensus",
        archive_dir: str = "logs/consensus/archive",
    ):
        self.log_dir = Path(log_dir)
        self.archive_dir = Path(archive_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._today: Optional[str] = None
        self._file_path: Optional[Path] = None
        self._rotate_if_needed()

    def _utc_day(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rotate_if_needed(self) -> None:
        day = self._utc_day()
        if day != self._today:
            # Archive yesterday's file if it exists
            if self._today is not None and self._file_path is not None:
                if self._file_path.exists():
                    archive_path = self.archive_dir / self._file_path.name
                    try:
                        os.replace(str(self._file_path), str(archive_path))
                        logger.info(
                            f"ConsensusAudit: archived "
                            f"{self._file_path.name} -> {archive_path}"
                        )
                    except Exception as e:
                        logger.error(f"ConsensusAudit: archive failed: {e}")
            self._today = day
            self._file_path = self.log_dir / f"{day}.jsonl"
            if not self._file_path.exists():
                self._file_path.touch()
                logger.info(f"ConsensusAudit: new day file {self._file_path}")

    @property
    def current_file(self) -> Optional[Path]:
        self._rotate_if_needed()
        return self._file_path

    def write(self, decision: Dict[str, Any]) -> None:
        self._rotate_if_needed()
        if self._file_path is None:
            logger.error("ConsensusAudit: no file path")
            return
        record = dict(decision)
        record.setdefault("ts", int(datetime.now(timezone.utc).timestamp() * 1000))
        record.setdefault("iso", datetime.now(timezone.utc).isoformat())
        try:
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            logger.error(f"ConsensusAudit: write failed: {e}")

    def read_day(self, day: str) -> List[Dict[str, Any]]:
        """Read all records for a day. Active first, then archive."""
        paths_to_try = [
            self.log_dir / f"{day}.jsonl",
            self.archive_dir / f"{day}.jsonl",
        ]
        for p in paths_to_try:
            if p.exists():
                records = []
                try:
                    with open(p, "r", encoding="utf-8-sig") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    records.append(json.loads(line))
                                except json.JSONDecodeError:
                                    logger.warning(
                                        f"ConsensusAudit: skipping malformed line in {p}"
                                    )
                except Exception as e:
                    logger.error(f"ConsensusAudit: read failed for {p}: {e}")
                return records
        return []

    def list_days(self) -> List[str]:
        """List all days present in active or archive."""
        days = set()
        for p in self.log_dir.glob("*.jsonl"):
            days.add(p.stem)
        for p in self.archive_dir.glob("*.jsonl"):
            days.add(p.stem)
        return sorted(days)

    def newest_active_day(self, min_size: int = 1) -> Optional[str]:
        """Return the most recent date (YYYY-MM-DD) of an active JSONL
        that has at least `min_size` bytes (or 1 line). Returns None if
        no candidate exists.

        Scans logs/consensus/*.jsonl (NOT archive). Chooses the lexically
        greatest filename stem that matches YYYY-MM-DD.
        """
        candidates = []
        for p in self.log_dir.glob("*.jsonl"):
            stem = p.stem
            # Validate format: YYYY-MM-DD
            parts = stem.split("-")
            if len(parts) != 3:
                continue
            try:
                int(parts[0]); int(parts[1]); int(parts[2])
            except ValueError:
                continue
            try:
                size = p.stat().st_size
            except Exception:
                continue
            if size >= min_size:
                candidates.append(stem)
        if not candidates:
            return None
        return sorted(candidates)[-1]

    def archive_day(self, day: str) -> Optional[Path]:
        """Manually move a day from active to archive."""
        src = self.log_dir / f"{day}.jsonl"
        if not src.exists():
            logger.warning(f"ConsensusAudit: nothing to archive for {day}")
            return None
        dst = self.archive_dir / src.name
        try:
            os.replace(str(src), str(dst))
            logger.info(f"ConsensusAudit: manual archive {src.name} -> {dst}")
            return dst
        except Exception as e:
            logger.error(f"ConsensusAudit: manual archive failed: {e}")
            return None
