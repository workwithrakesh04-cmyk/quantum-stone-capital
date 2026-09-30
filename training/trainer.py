"""Trainer - orchestrates the daily training cycle.

1. Reads target day's JSONL via ConsensusAudit
   - If day not given: auto-detect newest active JSONL
   - Fallback: UTC today
2. Loads previous trained state via current.json pointer
3. Computes new strategy weights + arbiter thresholds
4. Writes data/models/brain/YYYY-MM-DD/
5. Updates current.json
6. Archives the JSONL
7. Returns a report
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

from consensus.audit import ConsensusAudit
from training.loader import TrainingLoader, TrainingSample
from training.strategy_weights import StrategyWeightTrainer
from training.arbiter_thresholds import ArbiterThresholdTrainer


def _read_json(path: Path):
    """Read JSON handling UTF-8 BOM."""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path: Path, data) -> None:
    """Write JSON without BOM, with LF newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, default=str)


class Trainer:
    def __init__(
        self,
        audit: Optional[ConsensusAudit] = None,
        state_dir: str = "data/models/brain",
        pointer_file: str = "data/models/brain/current.json",
        strategy_bounds: Optional[Dict[str, Any]] = None,
        arbiter_bounds: Optional[Dict[str, Any]] = None,
        archive_after: bool = True,
    ):
        self.audit = audit or ConsensusAudit()
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pointer_file = Path(pointer_file)
        self.archive_after = archive_after

        self.loader = TrainingLoader(audit=self.audit)
        self.strategy_trainer = StrategyWeightTrainer(bounds=strategy_bounds)
        self.arbiter_trainer = ArbiterThresholdTrainer(bounds=arbiter_bounds)

    # ------------------------------------------------------------------
    # Day resolution
    # ------------------------------------------------------------------
    def _resolve_day(self, day: Optional[str]) -> str:
        """If day is None: pick newest active JSONL. Else UTC today."""
        if day:
            return day
        newest = self.audit.newest_active_day()
        if newest:
            logger.info(f"Trainer: auto-detected newest active day = {newest}")
            return newest
        fallback = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info(f"Trainer: no active JSONL found, defaulting to UTC today = {fallback}")
        return fallback

    # ------------------------------------------------------------------
    # Previous state helpers
    # ------------------------------------------------------------------
    def _read_pointer(self) -> Optional[str]:
        if not self.pointer_file.exists():
            return None
        try:
            return _read_json(self.pointer_file).get("active")
        except Exception as e:
            logger.warning(f"Trainer: pointer read failed: {e}")
            return None

    def _load_previous_weights(self) -> Dict[str, float]:
        active = self._read_pointer()
        if not active:
            return {}
        path = self.state_dir / active / "strategy_weights.json"
        if not path.exists():
            return {}
        try:
            return _read_json(path)
        except Exception as e:
            logger.warning(f"Trainer: previous weights read failed: {e}")
            return {}

    def _load_previous_thresholds(self) -> Dict[str, Any]:
        active = self._read_pointer()
        if not active:
            return {}
        path = self.state_dir / active / "arbiter_thresholds.json"
        if not path.exists():
            return {}
        try:
            return _read_json(path)
        except Exception as e:
            logger.warning(f"Trainer: previous thresholds read failed: {e}")
            return {}

    # ------------------------------------------------------------------
    # Writer helpers
    # ------------------------------------------------------------------
    def _write_pointer(self, day: str) -> None:
        _write_json(self.pointer_file, {
            "active": day,
            "updated": datetime.now(timezone.utc).isoformat(),
        })

    def _write_day_folder(
        self,
        day: str,
        strategy_weights: Dict[str, float],
        arbiter_thresholds: Dict[str, Any],
        strategy_report: Dict[str, Any],
        arbiter_report: Dict[str, Any],
        sample_count: int,
        no_op: bool,
    ) -> Path:
        folder = self.state_dir / day
        folder.mkdir(parents=True, exist_ok=True)

        _write_json(folder / "strategy_weights.json", strategy_weights)
        _write_json(folder / "arbiter_thresholds.json", arbiter_thresholds)
        _write_json(folder / "training_report.json", {
            "strategy_weights": strategy_report,
            "arbiter_thresholds": arbiter_report,
            "sample_count": sample_count,
            "no_op": no_op,
        })
        _write_json(folder / "meta.json", {
            "day": day,
            "created": datetime.now(timezone.utc).isoformat(),
            "samples": sample_count,
            "no_op": no_op,
        })
        logger.info(f"Trainer: wrote state folder {folder}")
        return folder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def train(self, day: Optional[str] = None) -> Dict[str, Any]:
        day = self._resolve_day(day)
        logger.info(f"Trainer: training for {day}")

        samples = self.loader.load_day(day)
        with_outcome = [s for s in samples if s.has_outcome()]

        prev_weights = self._load_previous_weights()
        prev_thresholds = self._load_previous_thresholds()

        new_weights = self.strategy_trainer.compute(
            with_outcome, previous_weights=prev_weights
        )
        new_thresholds = self.arbiter_trainer.compute(with_outcome)

        strategy_report = self.strategy_trainer.report(
            with_outcome, new_weights, prev=prev_weights
        )
        arbiter_report = self.arbiter_trainer.report(with_outcome, new_thresholds)

        no_op = len(with_outcome) == 0
        folder = self._write_day_folder(
            day=day,
            strategy_weights=new_weights,
            arbiter_thresholds=new_thresholds,
            strategy_report=strategy_report,
            arbiter_report=arbiter_report,
            sample_count=len(samples),
            no_op=no_op,
        )

        self._write_pointer(day)

        archived = None
        if self.archive_after and not no_op:
            archived = self.audit.archive_day(day)
            if archived:
                logger.info(f"Trainer: archived {day}")

        return {
            "day": day,
            "samples": len(samples),
            "samples_with_outcome": len(with_outcome),
            "no_op": no_op,
            "state_folder": str(folder),
            "archived": str(archived) if archived else None,
            "strategy_weights_updated": strategy_report["n_strategies_updated"],
            "regimes_analyzed": arbiter_report["n_regimes_analyzed"],
        }


def train_for_day(day: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    return Trainer(**kwargs).train(day=day)
