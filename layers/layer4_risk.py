"""Layer 4 - Risk. Wraps RiskEngine."""
import yaml
from core.risk_engine import RiskEngine


class Layer4Risk:
    def __init__(self, config_path: str = "config/master.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.engine = RiskEngine(self.config)

    def position_size(self, capital, risk_pct, entry, stop):
        return self.engine.calculate_position_size(capital, risk_pct, entry, stop)

    def validate(self, trade):
        return self.engine.validate_trade(trade)

    def var(self, returns, confidence=0.95):
        return self.engine.value_at_risk(returns, confidence)
