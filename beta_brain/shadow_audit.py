"""Shadow Audit - JSONL writer for D8 shadow runs.

Writes to logs/shadow/YYYY-MM-DD.jsonl (separate from
logs/consensus/ so the two logs do not mix). Rotates at UTC day
boundary, archives to logs/shadow/archive/.

API mirrors consensus.audit.ConsensusAudit for familiarity:
  - write(record)          append one record
  - read_day(day)          read all records for a UTC day
  - list_days()            all days with active or archived files
  - newest_active_day()    most recent non-empty active day
  - archive_day(day)       move active file to archive

Reader is encoding-tolerant (UTF-8 / UTF-8-sig / UTF-16 / latin-1).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


_ENCODINGS = ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1")


class ShadowAudit:
    def __init__(
        self,
        log_dir: str = "logs/shadow",
        archive_dir: str = "logs/shadow/archive",
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
            # Archive yesterday's file if it exists and is not empty
            if self._today is not None and self._file_path is not None:
                if self._file_path.exists() and self._file_path.stat().st_size > 0:
                    archive_path = self.archive_dir / self._file_path.name
                    try:
                        os.replace(str(self._file_path), str(archive_path))
                        logger.info(
                            f"ShadowAudit: archived {self._file_path.name} "
                            f"-> {archive_path}"
                        )
                    except Exception as e:
                        logger.error(f"ShadowAudit: archive failed: {e}")
            self._today = day
            self._file_path = self.log_dir / f"{day}.jsonl"
            if not self._file_path.exists():
                self._file_path.touch()
                logger.info(f"ShadowAudit: new day file {self._file_path}")

    @property
    def current_file(self) -> Optional[Path]:
        self._rotate_if_needed()
        return self._file_path

    def write(self, record: Dict[str, Any]) -> None:
        self._rotate_if_needed()
        if self._file_path is None:
            logger.error("ShadowAudit: no file path")
            return
        out = dict(record)
        out.setdefault(
            "ts", int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        out.setdefault("iso", datetime.now(timezone.utc).isoformat())
        try:
            with open(self._file_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(out, default=str) + "\n")
        except Exception as e:
            logger.error(f"ShadowAudit: write failed: {e}")

    def write_many(self, records: List[Dict[str, Any]]) -> int:
        """Write several records. Returns count written."""
        n = 0
        for r in records:
            self.write(r)
            n += 1
        return n

    @staticmethod
    def _read_lines(path: Path) -> Optional[List[str]]:
        for enc in _ENCODINGS:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read().splitlines()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.warning(f"ShadowAudit: open failed ({enc}): {e}")
                continue
        logger.error(f"ShadowAudit: no encoding worked for {path}")
        return None

    def read_day(self, day: str) -> List[Dict[str, Any]]:
        """Read all records for a UTC day (active first, then archive)."""
        for p in (self.log_dir / f"{day}.jsonl",
                  self.archive_dir / f"{day}.jsonl"):
            if not p.exists():
                continue
            lines = self._read_lines(p)
            if lines is None:
                return []
            records = []
            for raw in lines:
                line = raw.strip()
                if not line:
                    continue
                line = line.lstrip("\ufeff\uFEFF")
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        f"ShadowAudit: skipping malformed line in {p}: "
                        f"{line[:80]}"
                    )
            return records
        return []

    def list_days(self) -> List[str]:
        days = set()
        for p in self.log_dir.glob("*.jsonl"):
            days.add(p.stem)
        for p in self.archive_dir.glob("*.jsonl"):
            days.add(p.stem)
        return sorted(days)

    def newest_active_day(self, min_size: int = 1) -> Optional[str]:
        candidates = []
        for p in self.log_dir.glob("*.jsonl"):
            stem = p.stem
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
        src = self.log_dir / f"{day}.jsonl"
        if not src.exists():
            logger.warning(f"ShadowAudit: nothing to archive for {day}")
            return None
        dst = self.archive_dir / src.name
        try:
            os.replace(str(src), str(dst))
            logger.info(f"ShadowAudit: manual archive {src.name} -> {dst}")
            return dst
        except Exception as e:
            logger.error(f"ShadowAudit: manual archive failed: {e}")
            return None