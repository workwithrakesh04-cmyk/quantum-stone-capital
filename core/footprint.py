"""
Footprint analysis: bid/ask at each price level within a bar,
absorption clusters, POC, and imbalance stacks.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FootprintLevel:
    price: float
    bid_volume: float
    ask_volume: float

    @property
    def delta(self) -> float:
        return self.ask_volume - self.bid_volume

    @property
    def total_volume(self) -> float:
        return self.bid_volume + self.ask_volume


@dataclass
class FootprintBar:
    levels: List[FootprintLevel] = field(default_factory=list)

    @property
    def total_volume(self) -> float:
        return sum(l.total_volume for l in self.levels)

    @property
    def poc(self) -> Optional[float]:
        """Point of Control: price with the highest total volume."""
        if not self.levels:
            return None
        best = max(self.levels, key=lambda l: l.total_volume)
        return best.price

    @property
    def delta(self) -> float:
        return sum(l.delta for l in self.levels)


class FootprintEngine:
    """Analyzes footprint bars for absorption and imbalance signals."""

    def build_bar(self, ticks: List[dict]) -> FootprintBar:
        """
        ticks: list of {"price": float, "volume": float, "side": "bid"|"ask"}
        """
        levels: Dict[float, FootprintLevel] = {}
        for t in ticks:
            price = float(t["price"])
            vol = float(t["volume"])
            side = t.get("side", "bid")
            if price not in levels:
                levels[price] = FootprintLevel(price=price, bid_volume=0.0, ask_volume=0.0)
            if side == "ask":
                levels[price].ask_volume += vol
            else:
                levels[price].bid_volume += vol
        sorted_levels = sorted(levels.values(), key=lambda l: l.price)
        return FootprintBar(levels=sorted_levels)

    def find_imbalances(
        self,
        bar: FootprintBar,
        ratio: float = 3.0,
    ) -> List[FootprintLevel]:
        """Return levels where bid/ask ratio exceeds threshold."""
        out = []
        for level in bar.levels:
            if level.bid_volume <= 0 or level.ask_volume <= 0:
                continue
            if max(level.bid_volume, level.ask_volume) / min(level.bid_volume, level.ask_volume) >= ratio:
                out.append(level)
        return out

    def detect_absorption(
        self,
        bar: FootprintBar,
        min_total_volume: float = 100.0,
    ) -> Optional[str]:
        """
        Absorption at extremes: large volume at top/bottom with opposite delta.
        Returns 'top_absorb' | 'bottom_absorb' | None
        """
        if not bar.levels or bar.total_volume < min_total_volume:
            return None
        top = bar.levels[-1]
        bottom = bar.levels[0]
        if top.total_volume > bar.total_volume * 0.3 and top.delta < 0:
            return "top_absorb"
        if bottom.total_volume > bar.total_volume * 0.3 and bottom.delta > 0:
            return "bottom_absorb"
        return None
