"""
Prop firm rule engine.
Unlike the personal account (which allows anything), the prop firm has
strict rules: max 5% daily loss, 10% static DD, no weekend holding,
news trading allowed, no consistency rule.
"""
from dataclasses import dataclass
from typing import Optional

from brokers.sim_broker import AccountState


@dataclass
class PropRuleResult:
    allowed: bool
    reason: str
    warnings: list


class PropRuleEngine:
    """
    Enforces the prop firm's rules:
      - Max risk per trade: 1%
      - Max daily loss: 5% (based on starting balance)
      - Max drawdown: 10% (static, from peak)
      - No weekend holding
      - News trading: ALLOWED
      - No consistency rule
      - Max concurrent positions: 5
    """

    def __init__(
        self,
        max_risk_per_trade: float = 0.01,
        max_daily_loss: float = 0.05,
        max_drawdown: float = 0.10,
        allow_weekend_holding: bool = False,
        allow_news_trading: bool = True,
        max_concurrent_positions: int = 5,
    ):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.allow_weekend_holding = allow_weekend_holding
        self.allow_news_trading = allow_news_trading
        self.max_concurrent_positions = max_concurrent_positions

    def evaluate(
        self,
        account: AccountState,
        risk_amount: float,
        is_news_time: bool = False,
        is_weekend: bool = False,
    ) -> PropRuleResult:
        warnings = []

        # 1. Risk per trade
        max_risk = self.max_risk_per_trade * account.starting_balance
        if risk_amount > max_risk:
            return PropRuleResult(
                allowed=False,
                reason="risk_exceeds_limit ($" + str(round(risk_amount, 2)) + " > $" + str(round(max_risk, 2)) + ")",
                warnings=warnings,
            )

        # 2. Daily loss
        if account.daily_loss_pct >= self.max_daily_loss:
            return PropRuleResult(
                allowed=False,
                reason="daily_loss_limit_hit (" + str(round(account.daily_loss_pct * 100, 2)) + "% >= 5%)",
                warnings=warnings,
            )

        # 3. Max drawdown (static, from peak)
        if account.drawdown_pct >= self.max_drawdown:
            return PropRuleResult(
                allowed=False,
                reason="max_drawdown_hit (" + str(round(account.drawdown_pct * 100, 2)) + "% >= 10%)",
                warnings=warnings,
            )

        # 4. Max concurrent positions
        if account.open_positions_count >= self.max_concurrent_positions:
            return PropRuleResult(
                allowed=False,
                reason="max_positions_reached (" + str(account.open_positions_count) + " >= " + str(self.max_concurrent_positions) + ")",
                warnings=warnings,
            )

        # 5. Weekend holding
        if is_weekend and not self.allow_weekend_holding:
            return PropRuleResult(
                allowed=False,
                reason="weekend_holding_not_allowed",
                warnings=warnings,
            )

        # 6. News trading (allowed but warn)
        if is_news_time and not self.allow_news_trading:
            return PropRuleResult(
                allowed=False,
                reason="news_trading_not_allowed",
                warnings=warnings,
            )
        if is_news_time:
            warnings.append("news_time")

        # Soft warnings
        if account.daily_loss_pct > self.max_daily_loss * 0.7:
            warnings.append("approaching_daily_loss")
        if account.drawdown_pct > self.max_drawdown * 0.7:
            warnings.append("approaching_max_drawdown")

        return PropRuleResult(allowed=True, reason="OK", warnings=warnings)
