"""Training Loader - reads a day's consensus JSONL + trade records
and produces training samples for the trainer.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from consensus.audit import ConsensusAudit


class TrainingSample:
    def __init__(self, record: Dict[str, Any]):
        self.raw = record
        self.ts = record.get("ts")
        self.symbol = record.get("symbol")
        self.qsc_direction = self._norm(record.get("qsc", {}).get("direction"))
        self.beta_direction = self._norm(record.get("beta", {}).get("direction"))
        self.consensus = record.get("arbiter", {}).get("consensus", "UNKNOWN")
        self.strategies = record.get("beta", {}).get("contributing_strategies", [])
        self.regime = record.get("beta", {}).get("regime", "UNKNOWN")
        self.trade_outcome = record.get("outcome", None)
        self.pnl_usd = record.get("pnl_usd", 0.0)

    @staticmethod
    def _norm(direction) -> str:
        if direction is None:
            return "HOLD"
        d = str(direction).upper()
        if d in ("BUY", "LONG"):
            return "LONG"
        if d in ("SELL", "SHORT"):
            return "SHORT"
        return "HOLD"

    def has_outcome(self) -> bool:
        return self.trade_outcome in ("WIN", "LOSS")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "symbol": self.symbol,
            "qsc_direction": self.qsc_direction,
            "beta_direction": self.beta_direction,
            "consensus": self.consensus,
            "strategies": self.strategies,
            "regime": self.regime,
            "trade_outcome": self.trade_outcome,
            "pnl_usd": self.pnl_usd,
        }


class TrainingLoader:
    def __init__(self, audit: Optional[ConsensusAudit] = None):
        self.audit = audit or ConsensusAudit()

    def load_day(self, day: str) -> List[TrainingSample]:
        records = self.audit.read_day(day)
        samples = [TrainingSample(r) for r in records]
        logger.info(f"TrainingLoader: loaded {len(samples)} samples for {day}")
        return samples

    def filter_with_outcome(self, samples: List[TrainingSample]) -> List[TrainingSample]:
        return [s for s in samples if s.has_outcome()]

    def group_by_consensus(self, samples: List[TrainingSample]) -> Dict[str, List[TrainingSample]]:
        out: Dict[str, List[TrainingSample]] = {}
        for s in samples:
            out.setdefault(s.consensus, []).append(s)
        return out

    def group_by_regime(self, samples: List[TrainingSample]) -> Dict[str, List[TrainingSample]]:
        out: Dict[str, List[TrainingSample]] = {}
        for s in samples:
            out.setdefault(s.regime, []).append(s)
        return out

    def stats(self, samples: List[TrainingSample]) -> Dict[str, Any]:
        by_consensus = self.group_by_consensus(samples)
        stats = {
            "total": len(samples),
            "with_outcome": len(self.filter_with_outcome(samples)),
            "by_consensus": {k: len(v) for k, v in by_consensus.items()},
        }
        return stats
