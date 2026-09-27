"""
Strategy Selector: given a MarketContext, choose the best-matching strategy
from the registry based on regime and timeframe.
"""
from typing import List, Optional
from strategies.registry import StrategyRegistry


class StrategySelector:
    def __init__(self, registry: Optional[StrategyRegistry] = None):
        self.registry = registry or StrategyRegistry(root="strategies")

    def select(
        self,
        regime: Optional[str],
        timeframe: Optional[str] = None,
        prefer: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Return strategy names that match regime + timeframe, sorted by preference.
        """
        if regime is None:
            return []
        candidates = self.registry.match_regime(regime, timeframe=timeframe)
        if prefer:
            # Put preferred strategies first
            preferred = [c for c in candidates if c in prefer]
            others = [c for c in candidates if c not in prefer]
            return preferred + others
        return candidates

    def first(
        self,
        regime: Optional[str],
        timeframe: Optional[str] = None,
        prefer: Optional[List[str]] = None,
    ) -> Optional[str]:
        matches = self.select(regime, timeframe, prefer)
        return matches[0] if matches else None

    def spec(self, name: str) -> Optional[dict]:
        return self.registry.get(name)
