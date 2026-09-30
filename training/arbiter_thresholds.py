"""Arbiter Thresholds - computes new thresholds per regime based on
yesterday's win rates across consensus types.
"""
from typing import Dict, Any, List
from collections import defaultdict
from loguru import logger

from training.loader import TrainingSample


DEFAULT_BOUNDS = {
    "both_agree_min_win_rate": 0.55,
    "beta_only_min_win_rate": 0.40,
    "qsc_only_min_win_rate": 0.40,
}

DEFAULT_THRESHOLDS = {
    "both_agree_size": 1.0,
    "beta_only_size": 0.5,
    "qsc_only_size": 0.5,
    "beta_disable_regimes": ["CHOPPY"],
}


class ArbiterThresholdTrainer:
    def __init__(
        self,
        bounds: Dict[str, Any] = None,
        thresholds: Dict[str, Any] = None,
    ):
        self.bounds = {**DEFAULT_BOUNDS, **(bounds or {})}
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def _regime_stats(self, samples: List[TrainingSample]) -> Dict[str, Dict[str, Dict[str, int]]]:
        """regime -> consensus -> {wins, losses, trades}"""
        out: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "trades": 0})
        )
        for s in samples:
            if not s.has_outcome():
                continue
            r = out[s.regime][s.consensus]
            r["trades"] += 1
            if s.trade_outcome == "WIN":
                r["wins"] += 1
            else:
                r["losses"] += 1
        return {reg: dict(v) for reg, v in out.items()}

    def compute(self, samples: List[TrainingSample]) -> Dict[str, Any]:
        regime_stats = self._regime_stats(samples)
        new = dict(self.thresholds)
        disable_regimes = set(new.get("beta_disable_regimes", []))

        for regime, by_consensus in regime_stats.items():
            beta_only = by_consensus.get("BETA_ONLY", {"wins": 0, "trades": 0})
            if beta_only["trades"] >= 5:
                beta_wr = beta_only["wins"] / beta_only["trades"]
                if beta_wr < self.bounds["beta_only_min_win_rate"]:
                    disable_regimes.add(regime)
                else:
                    disable_regimes.discard(regime)

        new["beta_disable_regimes"] = sorted(disable_regimes)
        logger.info(f"ArbiterThresholdTrainer: {len(regime_stats)} regimes analyzed, "
                    f"beta disabled in {new['beta_disable_regimes']}")
        return new

    def report(self, samples: List[TrainingSample], new_thresholds: Dict[str, Any]) -> Dict[str, Any]:
        stats = self._regime_stats(samples)
        return {
            "n_regimes_analyzed": len(stats),
            "regime_stats": stats,
            "new_thresholds": new_thresholds,
        }
