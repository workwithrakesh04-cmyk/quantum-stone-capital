"""Rollback - manual pointer switch to a previous trained day."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


def _read_json(path: Path):
    """Read JSON handling UTF-8 BOM (PowerShell default on Windows)."""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    """Write JSON without BOM so any reader handles it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)


class Rollback:
    def __init__(
        self,
        state_dir: str = "data/models/brain",
        pointer_file: str = "data/models/brain/current.json",
    ):
        self.state_dir = Path(state_dir)
        self.pointer_file = Path(pointer_file)

    def list_available(self) -> List[str]:
        if not self.state_dir.exists():
            return []
        days = []
        for p in self.state_dir.iterdir():
            if p.is_dir():
                meta = p / "meta.json"
                if meta.exists():
                    days.append(p.name)
        return sorted(days)

    def current(self) -> Optional[str]:
        if not self.pointer_file.exists():
            return None
        try:
            return _read_json(self.pointer_file).get("active")
        except Exception as e:
            logger.error(f"Rollback: read failed: {e}")
            return None

    def rollback(self, day: str) -> bool:
        folder = self.state_dir / day
        if not folder.exists():
            logger.error(f"Rollback: state folder {folder} not found")
            return False
        meta = folder / "meta.json"
        if not meta.exists():
            logger.error(f"Rollback: no meta.json in {folder}")
            return False

        _write_json(self.pointer_file, {
            "active": day,
            "updated": datetime.now(timezone.utc).isoformat(),
            "rolled_back": True,
        })
        logger.info(f"Rollback: switched current pointer to {day}")
        return True

    def report(self) -> Dict[str, Any]:
        return {
            "available_days": self.list_available(),
            "current": self.current(),
        }
