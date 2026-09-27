"""
Strategy Registry.
Discovers strategy YAML files under strategies/, loads them,
and matches them to market regimes and timeframes.
"""
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class StrategyRegistry:
    """Central registry of all formalized trading strategies."""

    def __init__(self, root: str = "strategies"):
        self.root = Path(root)
        self.strategies: Dict[str, dict] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Recursively load every .yaml file under strategies/."""
        if not self.root.exists():
            return
        for path in sorted(self.root.rglob("*.yaml")):
            if path.name.startswith("_"):
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as exc:
                print("WARN: failed to load " + str(path) + ": " + str(exc))
                continue

            for name, spec in (data.get("strategies") or {}).items():
                spec = dict(spec)
                spec["_source_file"] = str(path)
                self.strategies[name] = spec

    def get(self, name: str) -> Optional[dict]:
        return self.strategies.get(name)

    def all_names(self) -> List[str]:
        return sorted(self.strategies.keys())

    def by_category(self, category: str) -> List[str]:
        return [n for n, s in self.strategies.items() if s.get("type") == category]

    def match_regime(
        self,
        regime: str,
        timeframe: Optional[str] = None,
    ) -> List[str]:
        """Return strategies matching regime and (optionally) timeframe."""
        matches = []
        for name, spec in self.strategies.items():
            if regime not in spec.get("regime", []):
                continue
            if timeframe is not None:
                tfs = spec.get("timeframes", [])
                if tfs and timeframe not in tfs:
                    continue
            matches.append(name)
        return matches

    def count(self) -> int:
        return len(self.strategies)
