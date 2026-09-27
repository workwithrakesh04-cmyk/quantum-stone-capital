"""
Strategy Juror: validates that the proposed trade matches a known strategy
with sufficient confluence and correct regime.
"""
from jurors.base_juror import BaseJuror, Verdict


class StrategyJuror(BaseJuror):
    name = "strategy"

    def __init__(self, min_confluence_score: float = 0.65):
        self.min_confluence_score = min_confluence_score

    def judge(self, proposal: dict) -> Verdict:
        warnings = []

        # 1. Strategy must be registered
        strategy_name = proposal.get("strategy_name")
        if not strategy_name:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="no strategy_name provided",
                warnings=["missing_strategy"],
            )

        # 2. Regime match
        strategy_regime = proposal.get("strategy_regime", [])
        current_regime = proposal.get("current_regime")
        if current_regime and strategy_regime and current_regime not in strategy_regime:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="regime mismatch: " + str(current_regime) + " not in " + str(strategy_regime),
                warnings=["regime_mismatch"],
            )

        # 3. Confluence score
        confluence = proposal.get("confluence_score", 0.0)
        if confluence < self.min_confluence_score:
            return Verdict(
                juror=self.name,
                approved=False,
                reason="confluence " + str(round(confluence, 2)) + " < min " + str(self.min_confluence_score),
                warnings=["low_confluence"],
            )

        # 4. Signal filter pass
        if not proposal.get("passes_filter", False):
            warnings.append("signal_not_extreme")

        # 5. Framework agreement (optional but strengthens)
        frameworks = proposal.get("agreeing_frameworks", [])
        if len(frameworks) < 2:
            warnings.append("few_frameworks_agree")

        return Verdict(
            juror=self.name,
            approved=True,
            reason="strategy validated: " + str(strategy_name),
            warnings=warnings,
        )
