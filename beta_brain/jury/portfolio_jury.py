"""Portfolio Jury - exposure, position count, correlation checks."""
from typing import Dict, Any
from loguru import logger

from beta_brain.debate.transcript import DebateTranscript
from beta_brain.jury.transcript import PortfolioVerdict, RiskVerdict
from beta_brain.account_guard import get_account_guard


class PortfolioJury:
    def __init__(self, config: dict):
        self.cfg = config
        self.modes = config["modes"]
        self.daily_limits = config.get("daily_limits", {})
        self.account_rules = config.get("account_rules", {})
        self.account_size = config["account"]["starting_balance"]

    def evaluate(
        self,
        debate: DebateTranscript,
        risk: RiskVerdict,
        portfolio_state: Dict[str, Any],
        mode: str = "scalp",
    ) -> PortfolioVerdict:
        if not risk.approved:
            return PortfolioVerdict(
                approved=False,
                reject_reason="risk jury rejected",
            )

        guard = get_account_guard(self.cfg)
        ok, reason = guard.check()
        if not ok:
            return PortfolioVerdict(
                approved=False,
                reject_reason=f"account guard: {reason}",
            )

        mode_cfg = self.modes.get(mode)
        if not mode_cfg or not mode_cfg.get("enabled"):
            return PortfolioVerdict(
                approved=False,
                reject_reason=f"mode {mode} not enabled",
            )

        open_pos = portfolio_state.get("open_positions", 0)
        max_pos = mode_cfg.get("max_open_positions", 1)
        if open_pos >= max_pos:
            return PortfolioVerdict(
                approved=False,
                current_open_positions=open_pos,
                max_positions_for_mode=max_pos,
                reject_reason=f"max {max_pos} positions for {mode}",
            )

        curr_risk_exposure = portfolio_state.get("current_exposure_pct", 0.0)
        new_risk_exposure = (risk.risk_amount_usd / self.account_size) * 100
        total_risk_exposure = curr_risk_exposure + new_risk_exposure

        max_risk_exposure = mode_cfg.get(
            "max_concurrent_risk_pct",
            mode_cfg.get("max_exposure_pct", 3.0),
        )
        if total_risk_exposure > max_risk_exposure:
            return PortfolioVerdict(
                approved=False,
                current_open_positions=open_pos,
                max_positions_for_mode=max_pos,
                current_exposure_pct=round(curr_risk_exposure, 2),
                max_exposure_pct=max_risk_exposure,
                reject_reason=f"risk exposure {total_risk_exposure:.2f}% > {max_risk_exposure}%",
            )

        notional_pct = (risk.position_size_usd / self.account_size) * 100
        leverage = notional_pct / 100

        daily_pnl = portfolio_state.get("daily_pnl_pct", 0.0)
        max_loss = self.account_rules.get("max_daily_loss_pct", 5.0)
        if daily_pnl <= -max_loss:
            return PortfolioVerdict(
                approved=False,
                current_open_positions=open_pos,
                max_positions_for_mode=max_pos,
                current_exposure_pct=round(curr_risk_exposure, 2),
                max_exposure_pct=max_risk_exposure,
                daily_pnl_pct=round(daily_pnl, 2),
                reject_reason=f"daily loss {daily_pnl:.2f}% hit limit -{max_loss}%",
            )

        logger.info(
            f"BetaPortfolioJury[{mode}]: APPROVED | "
            f"pos={open_pos+1}/{max_pos} "
            f"risk_exp={total_risk_exposure:.2f}%/{max_risk_exposure}%"
        )

        return PortfolioVerdict(
            approved=True,
            current_open_positions=open_pos,
            max_positions_for_mode=max_pos,
            current_exposure_pct=round(curr_risk_exposure, 2),
            max_exposure_pct=max_risk_exposure,
            daily_pnl_pct=round(daily_pnl, 2),
            notes=[
                f"position {open_pos+1}/{max_pos}",
                f"risk exposure {total_risk_exposure:.2f}%",
                f"notional {notional_pct:.0f}% (leverage {leverage:.1f}x)",
            ],
        )
