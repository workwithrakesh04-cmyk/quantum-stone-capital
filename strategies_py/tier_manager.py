"""Tier Manager - loads strategy_tiers.yaml and provides queries."""
import yaml
from typing import Dict, List, Set, Optional
from loguru import logger


class TierManager:
    def __init__(self, config_path: str = "config/strategy_tiers.yaml"):
        self.config_path = config_path
        with open(config_path, "r", encoding="utf-8-sig") as f:
            self.cfg = yaml.safe_load(f)

        self.tiers = self.cfg.get("tiers", {})
        self.accounts = self.cfg.get("accounts", {})

        self.strategy_to_tier: Dict[str, str] = {}
        self.tier_to_strategies: Dict[str, List[str]] = {}

        for tier_name, tier_def in self.tiers.items():
            strategies = tier_def.get("strategies", [])
            self.tier_to_strategies[tier_name] = strategies
            for s in strategies:
                self.strategy_to_tier[s] = tier_name

        logger.info(
            f"TierManager: {len(self.tiers)} tiers, "
            f"{len(self.strategy_to_tier)} strategies mapped"
        )

    def get_tier(self, strategy_name: str) -> Optional[str]:
        return self.strategy_to_tier.get(strategy_name)

    def get_tier_config(self, tier_name: str) -> dict:
        return self.tiers.get(tier_name, {})

    def get_weight(self, strategy_name: str) -> float:
        tier = self.get_tier(strategy_name)
        if not tier:
            return 0.5
        return self.tiers[tier].get("weight", 0.5)

    def get_trade_cap(self, strategy_name: str) -> int:
        tier = self.get_tier(strategy_name)
        if not tier:
            return 20
        return self.tiers[tier].get("trade_cap", 20)

    def get_enabled_strategies(self, account_type: str) -> Set[str]:
        acc = self.accounts.get(account_type, {})
        enabled_tiers = acc.get("enabled_tiers", [])
        enabled = set()
        for tier_name in enabled_tiers:
            enabled.update(self.tier_to_strategies.get(tier_name, []))
        return enabled

    def get_disabled_strategies(self, account_type: str) -> Set[str]:
        acc = self.accounts.get(account_type, {})
        disabled_tiers = acc.get("disabled_tiers", [])
        disabled = set()
        for tier_name in disabled_tiers:
            disabled.update(self.tier_to_strategies.get(tier_name, []))
        return disabled

    def is_enabled_for_account(self, strategy_name: str, account_type: str) -> bool:
        return strategy_name in self.get_enabled_strategies(account_type)

    def stats(self) -> dict:
        return {
            "tiers": list(self.tiers.keys()),
            "strategies_per_tier": {t: len(s) for t, s in self.tier_to_strategies.items()},
            "accounts": list(self.accounts.keys()),
        }


_manager = None


def get_tier_manager() -> TierManager:
    global _manager
    if _manager is None:
        _manager = TierManager()
    return _manager
