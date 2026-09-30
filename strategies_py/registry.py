"""StrategyRegistry - runs registered Beta strategies with regime filtering."""
from typing import List, Dict, Type, Optional
import yaml
from loguru import logger

from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class StrategyRegistry:
    def __init__(
        self,
        timeframe: str = "5m",
        filter_config_path: str = "config/strategy_regime_filters.yaml",
        tier_config_path: Optional[str] = "config/strategy_tiers.yaml",
    ):
        self.timeframe = timeframe
        self.active_strategies: Dict[str, BaseStrategy] = {}
        self.shadow_strategies: Dict[str, BaseStrategy] = {}
        self._registered_classes: List[Type[BaseStrategy]] = []

        self.global_disable = set()
        self.regime_rules: Dict = {}
        self.regime_enable_only: Dict = {}
        self.trade_caps: Dict = {}
        self.confidence_overrides: Dict = {}
        self.disabled_mode = "shadow"
        self._fire_counts: Dict[str, int] = {}

        try:
            with open(filter_config_path, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f) or {}
            self.global_disable = set(cfg.get("global_disable", []))
            self.regime_rules = cfg.get("regime_rules", {})
            self.regime_enable_only = cfg.get("regime_enable_only", {})
            self.trade_caps = cfg.get("trade_caps", {})
            self.confidence_overrides = cfg.get("regime_confidence_overrides", {})
            self.disabled_mode = cfg.get("system", {}).get("disabled_strategy_mode", "shadow")
            logger.info(f"BetaRegistry: {len(self.global_disable)} global disables loaded")
        except FileNotFoundError:
            logger.warning(f"BetaRegistry: no filter config at {filter_config_path}")

        self.tier_manager = None
        if tier_config_path:
            try:
                from strategies_py.tier_manager import TierManager
                self.tier_manager = TierManager(tier_config_path)
                logger.info("BetaRegistry: tier_manager loaded")
            except FileNotFoundError:
                logger.warning(f"BetaRegistry: no tier config at {tier_config_path}")

    def register(self, strategy_cls: Type[BaseStrategy]) -> None:
        self._registered_classes.append(strategy_cls)

    def register_all(self, classes: List[Type[BaseStrategy]]) -> None:
        for cls in classes:
            self.register(cls)

    def instantiate_all(self) -> None:
        self.active_strategies.clear()
        self.shadow_strategies.clear()

        for cls in self._registered_classes:
            try:
                if self.timeframe not in cls.TIMEFRAMES:
                    continue
                name = cls.NAME
                if name in self.global_disable:
                    if self.disabled_mode == "disabled":
                        continue
                    self.shadow_strategies[name] = cls(timeframe=self.timeframe)
                    continue
                self.active_strategies[name] = cls(timeframe=self.timeframe)
            except Exception as e:
                logger.error(f"BetaRegistry: failed to instantiate {cls.__name__}: {e}")

        logger.info(
            f"BetaRegistry: {len(self.active_strategies)} active, "
            f"{len(self.shadow_strategies)} shadow"
        )

    def _is_active(self, strategy_name: str, regime: Optional[str]) -> bool:
        if strategy_name in self.regime_enable_only:
            if regime not in self.regime_enable_only[strategy_name]:
                return False
        if regime and regime in self.regime_rules:
            if strategy_name in self.regime_rules[regime].get("block", []):
                return False
        cap = self.trade_caps.get(strategy_name)
        if cap is not None and self._fire_counts.get(strategy_name, 0) >= cap:
            return False
        return True

    def reset_fire_counts(self) -> None:
        self._fire_counts = {}

    def get_min_confidence(self, regime: Optional[str]) -> float:
        if regime and regime in self.confidence_overrides:
            return self.confidence_overrides[regime].get("min_debate_confidence", 0.7)
        return 0.7

    def run_all(self, candles: List[dict], regime: Optional[str] = None) -> List[Signal]:
        signals: List[Signal] = []
        for name, strat in self.active_strategies.items():
            if not self._is_active(name, regime):
                continue
            try:
                sig = strat.analyze(candles)
                signals.append(sig)
                if sig.direction in ("LONG", "SHORT"):
                    self._fire_counts[name] = self._fire_counts.get(name, 0) + 1
            except Exception as e:
                logger.error(f"BetaRegistry: strategy {name} failed: {e}")
        return signals

    def run_shadow(self, candles: List[dict], regime: Optional[str] = None) -> List[Signal]:
        signals: List[Signal] = []
        for name, strat in self.shadow_strategies.items():
            try:
                signals.append(strat.analyze(candles))
            except Exception as e:
                logger.debug(f"BetaRegistry: shadow {name} failed: {e}")
        return signals

    def actionable_signals(self, candles: List[dict], regime: Optional[str] = None) -> List[Signal]:
        return [s for s in self.run_all(candles, regime) if s.is_actionable()]

    def stats(self) -> dict:
        return {
            "timeframe": self.timeframe,
            "active": len(self.active_strategies),
            "shadow": len(self.shadow_strategies),
            "active_names": list(self.active_strategies.keys()),
            "has_tier_manager": self.tier_manager is not None,
        }
