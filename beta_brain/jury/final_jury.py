"""Final Jury - combines Risk + Portfolio verdicts (both must approve)."""
from loguru import logger

from beta_brain.jury.transcript import RiskVerdict, PortfolioVerdict, JuryVerdict
from beta_brain.debate.transcript import DebateTranscript


class FinalJury:
    def evaluate(
        self,
        debate: DebateTranscript,
        risk: RiskVerdict,
        portfolio: PortfolioVerdict,
        symbol: str = "BTCUSD",
        mode: str = "scalp",
        account_type: str = "personal",
    ) -> JuryVerdict:
        if risk.approved and portfolio.approved:
            final = "APPROVED"
            reason = (
                f"{account_type.upper()}/{mode.upper()} trade approved: "
                f"qty={risk.position_size_qty} SL={risk.stop_loss_price} "
                f"TP={risk.take_profit_price} RR={risk.risk_reward_ratio}"
            )
            logger.success(f"BetaJury[{account_type}]: {final} | {reason}")
        else:
            final = "REJECTED"
            reasons = []
            if not risk.approved:
                reasons.append(f"risk: {risk.reject_reason}")
            if not portfolio.approved:
                reasons.append(f"portfolio: {portfolio.reject_reason}")
            reason = " | ".join(reasons)
            logger.info(f"BetaJury[{account_type}]: {final} | {reason}")

        return JuryVerdict(
            ts=debate.ts,
            symbol=symbol,
            mode=mode,
            account_type=account_type,
            debate_winner=debate.winner,
            debate_confidence=debate.winner_confidence,
            risk=risk,
            portfolio=portfolio,
            final_decision=final,
            final_reason=reason,
        )
