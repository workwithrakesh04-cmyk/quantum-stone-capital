"""
Main Brain v2: end-to-end decision pipeline.

Flow:
  MarketContext -> Account check -> Strategy select -> Build proposal
    -> Debate Engine (workers + jurors) -> PipelineResult
"""
from typing import Optional
import yaml

from core.market_context import MarketContext
from core.pipeline_result import PipelineResult
from core.trade_proposal import TradeProposal
from core.strategy_selector import StrategySelector
from core.debate_engine import DebateEngine
from core.account_manager import AccountManager
from core.risk_engine import RiskEngine
from microstructure.engine import MicrostructureEngine
from strategies.signal_filter import SignalFilter


class MainBrainV2:
    def __init__(
        self,
        config_path: str = "config/master.yaml",
        registry_root: str = "strategies",
    ):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.account_mgr = AccountManager(config_path)
        self.risk_engine = RiskEngine(self.config)
        self.micro = MicrostructureEngine(
            sigma_u=self.config["microstructure"]["kyle_lambda"].get("sigma_u_default", 1.0),
        )
        self.selector = StrategySelector()
        self.signal_filter = SignalFilter(
            min_z_score=self.config["microstructure"]["signal_filter"]["min_z_score"],
            scale_max=3.0,
        )
        self.debate = DebateEngine()

    # ---------- public entry point ----------

    def run(
        self,
        context: MarketContext,
        account_name: str = "personal",
        risk_pct: Optional[float] = None,
        prefer_strategies: Optional[list] = None,
    ) -> PipelineResult:
        result = PipelineResult()
        result.layers_passed.append("layer0_data")

        # Layer 1: account rules sanity
        if account_name not in self.account_mgr.accounts:
            result.reasons.append("unknown_account")
            return result
        result.layers_passed.append("layer1_account_rules")

        # Layer 2: pricing / fair value (lightweight)
        if context.last_price is None:
            result.reasons.append("no_price_data")
            return result
        result.layers_passed.append("layer2_pricing")

        # Layer 3: strategy selection
        strategy_name = self.selector.first(
            regime=context.regime,
            timeframe=context.timeframe,
            prefer=prefer_strategies,
        )
        if strategy_name is None:
            result.reasons.append("no_matching_strategy")
            return result
        spec = self.selector.spec(strategy_name) or {}
        result.strategy_name = strategy_name
        result.layers_passed.append("layer3_strategies")

        # Layer 4: risk (position size and RR check happen inside proposal)

        # Compute signal score (extreme filter)
        if context.momentum is not None and context.closes:
            history = context.closes[-50:]
            score = self.signal_filter.score(context.momentum, history)
            result.metadata["signal_score"] = score
            context.signal_score = score
            context.passes_filter = score > 0.0

        # Layer 5-6: debate
        debate_context = self._context_to_debate_dict(context)
        proposal = self._build_proposal(
            context=context, spec=spec, strategy_name=strategy_name,
            account_name=account_name, risk_pct=risk_pct,
        )
        debate_result = self.debate.debate(debate_context, proposal.to_dict())
        result.layers_passed.append("layer6_debate")

        # Layer 7: final
        result.decision = debate_result.decision
        result.direction = debate_result.direction
        result.confidence = debate_result.confidence
        result.reasons.extend(debate_result.reasons)

        if debate_result.decision == "trade":
            result.entry_price = proposal.entry_price
            result.stop_loss = proposal.stop_loss
            result.take_profit = proposal.take_profit
            result.position_size = proposal.position_size
            result.rr_ratio = proposal.rr_ratio
            result.risk_pct = proposal.risk_pct
            result.order_type = proposal.order_type

        # Collect juror warnings
        for v in debate_result.verdicts:
            result.warnings.extend(v.warnings)
        result.layers_passed.append("layer7_main_brain")
        return result

    # ---------- helpers ----------

    def _context_to_debate_dict(self, ctx: MarketContext) -> dict:
        return {
            "momentum": ctx.momentum,
            "rsi": ctx.rsi,
            "bos": ctx.bos,
            "delta": ctx.delta,
            "regime": ctx.regime,
            "session": ctx.session,
            "is_weekend": ctx.is_weekend,
            "is_illiquid": ctx.is_illiquid,
            "volatility": ctx.volatility,
            "passes_filter": ctx.passes_filter,
            "harmonic_bullish": ctx.harmonic_bullish,
            "harmonic_bearish": ctx.harmonic_bearish,
            "wave3_active": ctx.wave3_active,
            "wave_c_active": ctx.wave_c_active,
        }

    def _build_proposal(
        self,
        context: MarketContext,
        spec: dict,
        strategy_name: str,
        account_name: str,
        risk_pct: Optional[float],
    ) -> TradeProposal:
        account = self.account_mgr.accounts[account_name]
        cfg = self.config["accounts"][account_name]
        risk_pct = risk_pct if risk_pct is not None else cfg["max_risk_per_trade"]

        entry = context.last_price or 0.0
        sl = self._stop_from_context(context, spec)
        tp = self._tp_from_context(context, spec)

        risk_per_unit = abs(entry - sl) if sl else 0.0
        reward_per_unit = abs(tp - entry) if tp else 0.0
        rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0

        size = 0.0
        if risk_per_unit > 0:
            size = self.risk_engine.calculate_position_size(
                account_capital=account.capital,
                risk_pct=risk_pct,
                entry=entry,
                stop_loss=sl,
            )

        return TradeProposal(
            symbol=context.symbol,
            direction="long" if (context.momentum or 0) >= 0 else "short",
            strategy_name=strategy_name,
            strategy_regime=spec.get("regime", []),
            current_regime=context.regime,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            rr_ratio=rr,
            risk_pct=risk_pct,
            position_size=size,
            daily_loss_pct=account.daily_loss_pct,
            drawdown_pct=account.drawdown,
            open_positions=len(account.open_positions),
            confluence_score=spec.get("min_confluence_score", 0.7),
            passes_filter=context.passes_filter,
            agreeing_frameworks=context.agreeing_frameworks,
            expected_slippage_pct=0.0002,
            expected_impact_pct=0.0002,
            session=context.session,
            active_killzones=context.active_killzones,
            order_type="limit",
            is_illiquid=context.is_illiquid,
        )

    def _stop_from_context(self, context: MarketContext, spec: dict) -> float:
        if context.lows:
            # Simple: recent swing low minus small buffer
            return min(context.lows[-10:]) * 0.999
        return (context.last_price or 0.0) * 0.99

    def _tp_from_context(self, context: MarketContext, spec: dict) -> float:
        if context.highs:
            return max(context.highs[-10:]) * 1.001
        return (context.last_price or 0.0) * 1.02
