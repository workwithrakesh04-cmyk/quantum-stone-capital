"""Verdict Engine - orchestrates the 3-jury decision for Beta Brain."""
from typing import List, Dict, Any, Optional
from loguru import logger

from beta_brain.debate.transcript import DebateTranscript
from beta_brain.jury.risk_jury import RiskJury
from beta_brain.jury.portfolio_jury import PortfolioJury
from beta_brain.jury.final_jury import FinalJury
from beta_brain.jury.transcript import JuryVerdict
from beta_brain.account_guard import get_account_guard


class VerdictEngine:
    def __init__(self, config: Optional[dict] = None):
        """Initialize with a config dict. If None, must call set_config()
        before use."""
        self._configs: Dict[str, dict] = {}
        self._risk_juries: Dict[str, RiskJury] = {}
        self._portfolio_juries: Dict[str, PortfolioJury] = {}
        self.final_jury = FinalJury()
        if config is not None:
            self.set_config("personal", config)

    def set_config(self, account_type: str, config: dict) -> None:
        self._configs[account_type] = config
        self._risk_juries[account_type] = RiskJury(config)
        self._portfolio_juries[account_type] = PortfolioJury(config)

    def _get_config(self, account_type: str) -> dict:
        if account_type not in self._configs:
            raise ValueError(
                f"VerdictEngine: no config for account '{account_type}'. "
                f"Call set_config() first."
            )
        return self._configs[account_type]

    def _get_risk_jury(self, account_type: str) -> RiskJury:
        if account_type not in self._risk_juries:
            self._get_config(account_type)  # raises if missing
        return self._risk_juries[account_type]

    def _get_portfolio_jury(self, account_type: str) -> PortfolioJury:
        if account_type not in self._portfolio_juries:
            self._get_config(account_type)
        return self._portfolio_juries[account_type]

    def run(
        self,
        debate: DebateTranscript,
        candles: List[dict],
        equity: float = 10000.0,
        portfolio_state: Optional[Dict[str, Any]] = None,
        mode: str = "scalp",
        account_type: str = "personal",
    ) -> JuryVerdict:
        if portfolio_state is None:
            portfolio_state = {
                "open_positions": 0,
                "current_exposure_pct": 0.0,
                "daily_pnl_pct": 0.0,
                "daily_trades": 0,
                "consecutive_losses": 0,
            }

        cfg = self._get_config(account_type)
        risk_jury = self._get_risk_jury(account_type)
        portfolio_jury = self._get_portfolio_jury(account_type)

        if candles:
            try:
                guard = get_account_guard(cfg)
                guard.daily_reset_if_needed(current_ts_ms=candles[-1]["open_time"])
            except Exception as e:
                logger.error(f"BetaVerdictEngine: daily_reset error: {e}")

        risk = risk_jury.evaluate(debate, candles, equity, mode)
        portfolio = portfolio_jury.evaluate(debate, risk, portfolio_state, mode)

        verdict = self.final_jury.evaluate(
            debate, risk, portfolio,
            symbol=debate.symbol, mode=mode,
            account_type=account_type,
        )
        return verdict

    def account_snapshot(self, account_type: str = "personal") -> dict:
        cfg = self._get_config(account_type)
        return get_account_guard(cfg).snapshot()
