"""Strategy Weights - computes new weight multipliers for Beta strategies
based on yesterday's win rate. Bounds enforced by config.
"""
from typing import Dict, Any, List
from collections import defaultdict
from loguru import logger

from training.loader import TrainingSample


DEFAULT_BOUNDS = {
    "min": 0.5,
    "max": 1.5,
    "win_rate_up_threshold": 0.55,
    "win_rate_down_threshold": 0.45,
    "up_step": 1.05,
    "down_step": 0.95,
}


class StrategyWeightTrainer:
    def __init__(self, bounds: Dict[str, Any] = None):
        self.bounds = {**DEFAULT_BOUNDS, **(bounds or {})}

    def _strategy_stats(self, samples: List[TrainingSample]) -> Dict[str, Dict[str, Any]]:
        stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        )
        for s in samples:
            if not s.has_outcome():
                continue
            for strat in s.strategies:
                stats[strat]["trades"] += 1
                stats[strat]["pnl"] += s.pnl_usd / max(1, len(s.strategies))
                if s.trade_outcome == "WIN":
                    stats[strat]["wins"] += 1
                else:
                    stats[strat]["losses"] += 1
        return dict(stats)

    def compute(
        self,
        samples: List[TrainingSample],
        previous_weights: Dict[str, float] = None,
    ) -> Dict[str, float]:
        prev = dict(previous_weights or {})
        stats = self._strategy_stats(samples)
        new_weights: Dict[str, float] = {}

        for strat, s in stats.items():
            trades = s["trades"]
            if trades < 3:
                # not enough data - keep previous (or default 1.0)
                new_weights[strat] = prev.get(strat, 1.0)
                continue
            win_rate = s["wins"] / trades
            current = prev.get(strat, 1.0)

            if win_rate >= self.bounds["win_rate_up_threshold"]:
                current *= self.bounds["up_step"]
            elif win_rate <= self.bounds["win_rate_down_threshold"]:
                current *= self.bounds["down_step"]

            current = max(self.bounds["min"], min(self.bounds["max"], current))
            new_weights[strat] = round(current, 4)

        # Preserve previous weights for strategies not seen today
        for strat, w in prev.items():
            if strat not in new_weights:
                new_weights[strat] = w

        logger.info(f"StrategyWeightTrainer: computed {len(new_weights)} weights from {len(samples)} samples")
        return new_weights

    def report(self, samples: List[TrainingSample], new_weights: Dict[str, float], prev: Dict[str, float] = None) -> Dict[str, Any]:
        prev = prev or {}
        stats = self._strategy_stats(samples)
        changes = {}
        for strat, w in new_weights.items():
            old = prev.get(strat, 1.0)
            if abs(w - old) > 1e-6:
                changes[strat] = {"old": old, "new": w, "trades": stats.get(strat, {}).get("trades", 0)}
        return {
            "n_strategies_updated": len(changes),
            "changes": changes,
            "weights": new_weights,
        }
