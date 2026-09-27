"""
TradeProposal: assembled by the Main Brain and handed to the jurors.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TradeProposal:
    # Identity
    symbol: str
    direction: str               # "long" | "short"

    # Strategy metadata
    strategy_name: str
    strategy_regime: List[str] = field(default_factory=list)
    current_regime: Optional[str] = None

    # Price plan
    entry_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Size and risk
    rr_ratio: float = 0.0
    risk_pct: float = 0.0
    position_size: float = 0.0

    # Account state
    daily_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    open_positions: int = 0

    # Confluence & filter
    confluence_score: float = 0.0
    passes_filter: bool = False
    agreeing_frameworks: List[str] = field(default_factory=list)

    # Execution hints
    expected_slippage_pct: float = 0.0
    expected_impact_pct: float = 0.0
    session: Optional[str] = None
    active_killzones: List[str] = field(default_factory=list)
    order_type: str = "limit"
    is_illiquid: bool = False

    def to_dict(self) -> dict:
        """Flatten to a dict for the jurors (which expect dicts)."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy_name": self.strategy_name,
            "strategy_regime": self.strategy_regime,
            "current_regime": self.current_regime,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rr_ratio": self.rr_ratio,
            "risk_pct": self.risk_pct,
            "position_size": self.position_size,
            "daily_loss_pct": self.daily_loss_pct,
            "drawdown_pct": self.drawdown_pct,
            "open_positions": self.open_positions,
            "confluence_score": self.confluence_score,
            "passes_filter": self.passes_filter,
            "agreeing_frameworks": self.agreeing_frameworks,
            "expected_slippage_pct": self.expected_slippage_pct,
            "expected_impact_pct": self.expected_impact_pct,
            "session": self.session,
            "active_killzones": self.active_killzones,
            "order_type": self.order_type,
            "is_illiquid": self.is_illiquid,
        }
