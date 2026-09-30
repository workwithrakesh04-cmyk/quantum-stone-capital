"""Signal - self-contained Signal dataclass for Beta Brain strategies.

Beta strategies (in strategies_py/) use this instead of QSC's
strategies.base_strategy.Signal. Keeps Beta Brain fully isolated.
"""
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Signal:
    strategy: str
    direction: str          # "LONG" | "SHORT" | "HOLD"
    confidence: float       # 0.0 to 1.0
    book_id: str = ""
    weight: float = 0.5
    reason: str = ""
    confluences: List[str] = field(default_factory=list)
    timeframe: str = "5m"
    price: float = 0.0
    ts: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def is_actionable(self) -> bool:
        return self.direction in ("LONG", "SHORT") and self.confidence >= 0.4

    def is_long(self) -> bool:
        return self.direction == "LONG"

    def is_short(self) -> bool:
        return self.direction == "SHORT"

    def is_hold(self) -> bool:
        return self.direction == "HOLD"
