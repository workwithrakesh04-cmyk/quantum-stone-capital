"""BetaBrain - full Beta Brain pipeline."""
import yaml
from loguru import logger

from beta_brain.regime_tagger import get_regime_tagger
from beta_brain.debate.engine import DebateEngine
from beta_brain.jury.verdict_engine import VerdictEngine
from strategies_py.registry import StrategyRegistry
from strategies_py.loader import load_all_strategies
from core.htf_bias import compute_htf_bias


class BetaBrain:
    def __init__(
        self,
        timeframe="5m",
        personal_config_path="config/beta_personal.yaml",
        prop_config_path="config/beta_prop.yaml",
        strategies_config_path="config/strategy_regime_filters.yaml",
        tiers_config_path="config/strategy_tiers.yaml",
    ):
        self.timeframe = timeframe
        self.regime_tagger = get_regime_tagger()
        self.registry = StrategyRegistry(
            timeframe=timeframe,
            filter_config_path=strategies_config_path,
            tier_config_path=tiers_config_path,
        )
        self.registry.register_all(load_all_strategies())
        self.registry.instantiate_all()
        self.debate = DebateEngine()
        self.jury = VerdictEngine()
        self._load_account("personal", personal_config_path)
        self._load_account("prop", prop_config_path)
        stats = self.registry.stats()
        logger.info("BetaBrain init | active=" + str(stats["active"]) + " shadow=" + str(stats["shadow"]))

    def _load_account(self, account_type, config_path):
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f)
            self.jury.set_config(account_type, cfg)
        except FileNotFoundError:
            logger.warning("BetaBrain: config not found at " + config_path)

    def run(self, context, account_type="personal", mode="scalp",
            equity=10000.0, portfolio_state=None):
        try:
            candles = self._context_to_candles(context)
            if len(candles) < 50:
                return None
            regime_tag = self.regime_tagger.tag(candles)
            regime = regime_tag.regime

            # HTF bias (uses LTF candles resampled internally)
            try:
                htf_bias = compute_htf_bias(candles)
            except Exception:
                htf_bias = None
            signals = self.registry.run_all(candles, regime=regime)
            actionable = [s for s in signals if s.direction in ("LONG", "SHORT")]
            if not actionable:
                return None
            debate = self.debate.run(signals, candles,
                                     symbol=getattr(context, "symbol", "UNKNOWN"),
                                     timeframe=self.timeframe)
            min_conf = self.registry.get_min_confidence(regime)
            if debate.winner_confidence < min_conf:
                return None
            if portfolio_state is None:
                portfolio_state = {"open_positions": 0, "current_exposure_pct": 0.0,
                                   "daily_pnl_pct": 0.0, "daily_trades": 0,
                                   "consecutive_losses": 0}
            verdict = self.jury.run(debate=debate, candles=candles, equity=equity,
                                    portfolio_state=portfolio_state, mode=mode,
                                    account_type=account_type)
            return verdict
        except Exception as e:
            logger.error("BetaBrain.run failed: " + str(e))
            return None

    def _context_to_candles(self, context):
        closes = getattr(context, "closes", []) or []
        highs = getattr(context, "highs", []) or []
        lows = getattr(context, "lows", []) or []
        opens = getattr(context, "opens", []) or []
        volumes = getattr(context, "volumes", []) or []
        n = len(closes)
        if n == 0:
            return []
        if len(highs) < n:
            highs = list(highs) + [closes[-1]] * (n - len(highs))
        if len(lows) < n:
            lows = list(lows) + [closes[-1]] * (n - len(lows))
        if len(opens) < n:
            opens = list(opens) + list(closes[:n - len(opens)])
        if len(volumes) < n:
            volumes = list(volumes) + [0.0] * (n - len(volumes))
        candles = []
        for i in range(n):
            candles.append({
                "open": float(opens[i]), "high": float(highs[i]),
                "low": float(lows[i]), "close": float(closes[i]),
                "volume": float(volumes[i]), "open_time": 0,
                "buy_volume": 0.0, "sell_volume": 0.0,
            })
        return candles

    def get_status(self):
        return {"timeframe": self.timeframe, "registry": self.registry.stats()}
