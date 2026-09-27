"""Risk Engine - Layer 4."""
import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class TradeRisk:
    entry: float
    stop_loss: float
    take_profit: float
    size: float
    instrument: str
    direction: str

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry - self.stop_loss)

    @property
    def reward_per_unit(self) -> float:
        return abs(self.take_profit - self.entry)

    @property
    def rr_ratio(self) -> float:
        if self.risk_per_unit == 0:
            return 0.0
        return self.reward_per_unit / self.risk_per_unit

    @property
    def total_risk(self) -> float:
        return self.risk_per_unit * self.size


class RiskEngine:
    def __init__(self, config: dict):
        self.config = config

    def calculate_position_size(
        self, account_capital, risk_pct, entry, stop_loss, contract_size=1.0
    ) -> float:
        risk_amount = account_capital * risk_pct
        risk_per_unit = abs(entry - stop_loss)
        if risk_per_unit == 0:
            return 0.0
        return risk_amount / (risk_per_unit * contract_size)

    def validate_trade(self, trade: TradeRisk) -> Tuple[bool, str]:
        min_rr = self.config["risk"]["min_rr_ratio"]
        if trade.rr_ratio < min_rr:
            return False, f"RR {trade.rr_ratio:.2f} < min {min_rr}"
        return True, "OK"

    def value_at_risk(self, returns, confidence=0.95, horizon_days=1) -> float:
        if len(returns) == 0:
            return 0.0
        var = np.percentile(returns, (1 - confidence) * 100)
        return var * np.sqrt(horizon_days)
