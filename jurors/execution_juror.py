"""
Execution Juror: validates that the trade can be executed cleanly.
Checks slippage, order size, session timing, and market microstructure.
"""
from jurors.base_juror import BaseJuror, Verdict


class ExecutionJuror(BaseJuror):
    name = "execution"

    def __init__(
        self,
        max_slippage_pct: float = 0.001,
        max_impact_pct: float = 0.001,
    ):
        self.max_slippage_pct = max_slippage_pct
        self.max_impact_pct = max_impact_pct

    def judge(self, proposal: dict) -> Verdict:
        warnings = []
        required_adjustments = []

        slippage = proposal.get("expected_slippage_pct", 0.0)
        if slippage > self.max_slippage_pct:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="slippage " + str(slippage) + " > max " + str(self.max_slippage_pct),
                warnings=["high_slippage"],
            )

        impact = proposal.get("expected_impact_pct", 0.0)
        if impact > self.max_impact_pct:
            required_adjustments.append("split_order_into_child_orders")
            warnings.append("impact_above_max")

        if proposal.get("is_illiquid", False):
            warnings.append("illiquid_market")

        session = proposal.get("session")
        if session == "off_hours":
            warnings.append("off_hours_trading")
        if session is None:
            warnings.append("unknown_session")

        active_kz = proposal.get("active_killzones", [])
        if not active_kz:
            warnings.append("outside_killzone")

        order_type = proposal.get("order_type")
        if order_type is None:
            required_adjustments.append("specify_order_type")
        elif order_type == "market" and impact > self.max_impact_pct / 2:
            required_adjustments.append("prefer_limit_order")

        approved = impact <= self.max_impact_pct
        reason = "execution validated" if approved else "impact above max - split order"

        return Verdict(
            juror=self.name,
            approved=approved,
            reason=reason,
            warnings=warnings,
            required_adjustments=required_adjustments,
        )
