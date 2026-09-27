"""
Risk Juror: enforces risk rules with VETO power.
Blocks trades that violate: account limits, RR, position size, drawdown, exposure.
"""
from jurors.base_juror import BaseJuror, Verdict


class RiskJuror(BaseJuror):
    name = "risk"

    def __init__(
        self,
        max_risk_per_trade: float = 0.01,
        min_rr_ratio: float = 2.0,
        max_daily_loss_pct: float = 0.03,
        max_drawdown_pct: float = 0.10,
        max_concurrent_positions: int = 5,
    ):
        self.max_risk_per_trade = max_risk_per_trade
        self.min_rr_ratio = min_rr_ratio
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_concurrent_positions = max_concurrent_positions

    def judge(self, proposal: dict) -> Verdict:
        warnings = []
        required_adjustments = []

        # 1. Reward/Risk ratio
        rr = proposal.get("rr_ratio", 0.0)
        if rr < self.min_rr_ratio:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="RR " + str(round(rr, 2)) + " < min " + str(self.min_rr_ratio),
                warnings=["low_rr"],
            )

        # 2. Risk per trade
        risk_pct = proposal.get("risk_pct", 0.0)
        if risk_pct > self.max_risk_per_trade:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="risk_pct " + str(round(risk_pct, 4)) + " > max " + str(self.max_risk_per_trade),
                warnings=["risk_per_trade_exceeded"],
            )

        # 3. Daily loss
        daily_loss = proposal.get("daily_loss_pct", 0.0)
        if daily_loss >= self.max_daily_loss_pct:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="daily_loss_pct " + str(round(daily_loss, 4)) + " >= max " + str(self.max_daily_loss_pct),
                warnings=["daily_loss_limit_hit"],
            )

        # 4. Drawdown
        dd = proposal.get("drawdown_pct", 0.0)
        if dd >= self.max_drawdown_pct:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="drawdown " + str(round(dd, 4)) + " >= max " + str(self.max_drawdown_pct),
                warnings=["max_drawdown_hit"],
            )

        # 5. Concurrent positions
        open_positions = proposal.get("open_positions", 0)
        if open_positions >= self.max_concurrent_positions:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="max concurrent positions reached",
                warnings=["too_many_positions"],
            )

        # 6. Stop loss must be present
        if proposal.get("stop_loss") is None:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="no stop_loss specified",
                warnings=["stop_loss_missing"],
            )

        # Non-fatal warnings
        if rr < 3.0:
            warnings.append("rr_below_3")
        if risk_pct > 0.008:
            warnings.append("risk_near_max")
        if daily_loss > self.max_daily_loss_pct * 0.7:
            warnings.append("approaching_daily_loss")

        return Verdict(
            juror=self.name,
            approved=True,
            reason="all risk checks passed",
            warnings=warnings,
            required_adjustments=required_adjustments,
        )
