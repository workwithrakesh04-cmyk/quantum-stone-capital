"""Jury Verdict schema - output of the 3-jury decision process."""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import json


@dataclass
class RiskVerdict:
    approved: bool
    mode: str
    position_size_usd: float = 0.0
    position_size_qty: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    risk_reward_ratio: float = 0.0
    risk_amount_usd: float = 0.0
    reject_reason: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PortfolioVerdict:
    approved: bool
    current_open_positions: int = 0
    max_positions_for_mode: int = 0
    current_exposure_pct: float = 0.0
    max_exposure_pct: float = 0.0
    daily_pnl_pct: float = 0.0
    reject_reason: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JuryVerdict:
    ts: int
    symbol: str
    mode: str
    debate_winner: str
    debate_confidence: float
    risk: RiskVerdict
    portfolio: PortfolioVerdict
    final_decision: str
    account_type: str = "personal"
    final_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "symbol": self.symbol,
            "mode": self.mode,
            "account_type": self.account_type,
            "debate_winner": self.debate_winner,
            "debate_confidence": self.debate_confidence,
            "risk": self.risk.to_dict(),
            "portfolio": self.portfolio.to_dict(),
            "final_decision": self.final_decision,
            "final_reason": self.final_reason,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)
