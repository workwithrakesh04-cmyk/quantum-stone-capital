"""Layer 1 — Account Rules. Wraps AccountManager as a layer."""
from core.account_manager import AccountManager


class Layer1AccountRules:
    def __init__(self, config_path: str = "config/master.yaml"):
        self.manager = AccountManager(config_path)

    def check_trade(self, account_name: str, risk_amount: float, instrument: str):
        return self.manager.can_open_trade(account_name, risk_amount, instrument)

    def register_trade(self, account_name: str, pnl: float):
        self.manager.register_trade(account_name, pnl)

    def status(self, account_name: str):
        return self.manager.get_status(account_name)
