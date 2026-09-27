"""
Account Router: decides which account should receive a signal.
Personal has priority unless unavailable; prop is the fallback when
the personal account's rules block trading.
"""
from dataclasses import dataclass
from typing import Optional

from brokers.broker_pool import BrokerPool
from brokers.sim_broker import AccountState
from core.prop_rules import PropRuleEngine


@dataclass
class RoutingDecision:
    account_name: str
    allowed: bool
    reason: str
    warnings: list
    rule_source: str  # "personal" | "prop_firm" | "both_blocked"


class AccountRouter:
    """
    Chooses the best account for a signal given account states + rules.
    """

    def __init__(self, pool: BrokerPool):
        self.pool = pool
        self.prop_rules = PropRuleEngine()

    def _check_personal(self, acc: AccountState, risk_amount: float,
                        is_news: bool, is_weekend: bool):
        """Personal account rules (looser)."""
        warnings = []
        if risk_amount > acc.max_risk_per_trade * acc.starting_balance:
            return False, "risk_exceeds_limit", warnings
        if acc.daily_loss_pct >= acc.max_daily_loss:
            return False, "daily_loss_limit_hit", warnings
        if acc.drawdown_pct >= acc.max_drawdown:
            return False, "max_drawdown_hit", warnings
        if acc.open_positions_count >= acc.max_concurrent_positions:
            return False, "max_positions_reached", warnings
        if is_weekend and not acc.allow_weekend_holding:
            return False, "weekend_holding_not_allowed", warnings
        if is_news and not acc.allow_news_trading:
            return False, "news_trading_not_allowed", warnings
        return True, "OK", warnings

    def route(
        self,
        risk_amount: float,
        preferred: str = "personal",
        is_news: bool = False,
        is_weekend: bool = False,
    ) -> RoutingDecision:
        """
        Pick the account that should receive the trade.
        Preference order: preferred account, then the other.
        """
        personal = self.pool.get_account("personal")
        prop = self.pool.get_account("prop")

        candidates = []
        if preferred == "personal":
            candidates = [("personal", personal), ("prop", prop)]
        else:
            candidates = [("prop", prop), ("personal", personal)]

        for name, acc in candidates:
            if acc is None:
                continue
            if name == "prop":
                result = self.prop_rules.evaluate(
                    account=acc,
                    risk_amount=risk_amount,
                    is_news_time=is_news,
                    is_weekend=is_weekend,
                )
                if result.allowed:
                    return RoutingDecision(
                        account_name=name,
                        allowed=True,
                        reason="prop_rules_passed",
                        warnings=result.warnings,
                        rule_source="prop_firm",
                    )
            else:
                ok, reason, warnings = self._check_personal(
                    acc, risk_amount, is_news, is_weekend
                )
                if ok:
                    return RoutingDecision(
                        account_name=name,
                        allowed=True,
                        reason="personal_rules_passed",
                        warnings=warnings,
                        rule_source="personal",
                    )

        # Both blocked
        return RoutingDecision(
            account_name=preferred,
            allowed=False,
            reason="all_accounts_blocked",
            warnings=[],
            rule_source="both_blocked",
        )
