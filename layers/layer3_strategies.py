"""Layer 3 - Strategies. Wraps StrategyRegistry + SignalFilter."""
from strategies.registry import StrategyRegistry
from strategies.signal_filter import SignalFilter


class Layer3Strategies:
    def __init__(
        self,
        registry_root: str = "strategies",
        min_z_score: float = 1.5,
        scale_max: float = 3.0,
    ):
        self.registry = StrategyRegistry(root=registry_root)
        self.filter = SignalFilter(min_z_score=min_z_score, scale_max=scale_max)

    def candidates(self, regime: str, timeframe: str = None):
        return self.registry.match_regime(regime, timeframe)

    def filter_signal(self, value, history):
        return self.filter.score(value, history)

    def passes_filter(self, value, history) -> bool:
        return self.filter.passes(value, history)
