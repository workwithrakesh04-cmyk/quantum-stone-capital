"""Main Brain - Layer 7. Central orchestrator."""
import yaml
from core.account_manager import AccountManager
from core.pricing_engine import PricingEngine
from core.risk_engine import RiskEngine


class MainBrain:
    def __init__(self, config_path: str = "config/master.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.account_manager = AccountManager(config_path)
        self.pricing_engine = PricingEngine()
        self.risk_engine = RiskEngine(self.config)

    def health_check(self) -> dict:
        return {
            "version": self.config["project"]["version"],
            "mode": self.config["project"]["mode"],
            "accounts": list(self.account_manager.accounts.keys()),
            "status": "OK",
        }
