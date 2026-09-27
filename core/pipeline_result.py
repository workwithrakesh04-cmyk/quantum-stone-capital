"""
PipelineResult: the single output shape from the Main Brain.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PipelineResult:
    # Decision
    decision: str = "no_trade"         # "trade" | "no_trade"
    direction: str = "flat"            # "long" | "short" | "flat"
    confidence: float = 0.0

    # Proposed trade
    strategy_name: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: float = 0.0
    rr_ratio: float = 0.0
    risk_pct: float = 0.0

    # Execution hints
    order_type: str = "limit"
    child_order_count: int = 1

    # Diagnostics
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    layers_passed: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def is_trade(self) -> bool:
        return self.decision == "trade"
