"""Beta Backtester - historical simulation of the Beta Brain pipeline.

D6c changes:
  - max_hold_bars derived from config; stage rejection counters; period_days
    threaded into performance metrics.

D7c changes:
  - confidence_histogram: buckets of winner_confidence for BUY/SELL winners,
    split by whether they passed the min-confidence gate.
  - volatile_by_strategy: per-strategy trades + PnL restricted to VOLATILE.
  - tmo_by_strategy: per-strategy trades + PnL + avg bars held for TMO exits.
"""
import asyncio
import time
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from loguru import logger

from feeds.historical_loader import HistoricalLoader
from beta_brain.regime_tagger import get_regime_tagger
from beta_brain.debate.engine import DebateEngine
from beta_brain.jury.verdict_engine import VerdictEngine
from beta_brain.paper_trader import PaperTrader
from beta_brain.strategy_analyzer import StrategyAnalyzer
from beta_brain.performance_metrics import enrich
from strategies_py.registry import StrategyRegistry
from strategies_py.loader import load_all_strategies


TIMEFRAME_MINUTES = {
    "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "1d": 1440,
}

# D7c: histogram bucket edges for winner_confidence
CONF_BUCKETS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    start_iso: str
    end_iso: str
    total_candles: int
    warmup: int
    runtime_sec: float
    stats: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BetaBacktester:
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "5m",
        account_type: str = "personal",
        config_path: str = "config/beta_personal.yaml",
        regime_filters_path: str = "config/strategy_regime_filters.yaml",
        tiers_path: str = "config/strategy_tiers.yaml",
        starting_balance: float = 10000.0,
        warmup: int = 100,
        max_window: int = 500,
        mode: str = "scalp",
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.account_type = account_type
        self.starting_balance = starting_balance
        self.warmup = warmup
        self.max_window = max_window
        self.mode = mode

        with open(config_path, "r", encoding="utf-8-sig") as f:
            self.account_cfg = yaml.safe_load(f)

        self.tagger = get_regime_tagger()

        self.registry = StrategyRegistry(
            timeframe=timeframe,
            filter_config_path=regime_filters_path,
            tier_config_path=tiers_path,
        )
        self.registry.register_all(load_all_strategies())
        self.registry.instantiate_all()

        self.debate = DebateEngine()
        self.jury = VerdictEngine()
        self.jury.set_config(account_type, self.account_cfg)

        self.analyzer = StrategyAnalyzer()
        self.trader = PaperTrader(
            account_type=account_type,
            starting_balance=starting_balance,
            on_trade_close=self._on_trade_close,
        )

        self.max_hold_bars = self._derive_max_hold_bars()

        # Tracking
        self.candles_processed = 0
        self.debates_run = 0
        self.trades_opened = 0
        self.trades_rejected = 0
        self.rejected_hold = 0
        self.rejected_low_confidence = 0
        self.rejected_risk_jury = 0
        self.rejected_portfolio_jury = 0

        # D7c: raw per-debate records for post-hoc aggregation
        # Each entry: {"winner": str, "confidence": float, "min_conf": float,
        #              "passed_gate": bool, "regime": str}
        self._debate_records: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------

    def _derive_max_hold_bars(self) -> int:
        rules = self.account_cfg.get("account_rules", {}) or {}
        if not rules.get("enable_timeout_exits", False):
            return 0

        modes = self.account_cfg.get("modes", {}) or {}
        mode_cfg = modes.get(self.mode, {}) or {}

        tf_min = TIMEFRAME_MINUTES.get(self.timeframe)
        if tf_min is None:
            logger.warning(
                f"BetaBacktester: unknown timeframe {self.timeframe}; max_hold_bars=0"
            )
            return 0

        minutes = mode_cfg.get("max_holding_minutes")
        if minutes is None:
            hours = mode_cfg.get("max_holding_hours")
            if hours is not None:
                minutes = int(hours) * 60
        if minutes is None:
            return 0
        return max(int(minutes) // tf_min, 1)

    def _on_trade_close(self, pnl_usd: float) -> None:
        if not self.trader.closed_trades:
            return
        t = self.trader.closed_trades[-1]
        self.analyzer.record_trade(
            contributing_strategies=list(t.contributing_strategies),
            direction=t.direction,
            pnl_usd=t.pnl_usd,
            regime=t.regime,
        )

    async def fetch_candles(self, total: int = 10000) -> List[dict]:
        loader = HistoricalLoader(symbol=self.symbol)
        return await loader.fetch_klines(timeframe=self.timeframe, limit=total)

    def _to_beta_candles(self, hist_candles: List[dict]) -> List[dict]:
        out = []
        for c in hist_candles:
            out.append({
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c.get("volume", 0.0)),
                "open_time": int(c.get("open_time", 0)),
                "buy_volume": 0.0,
                "sell_volume": 0.0,
            })
        return out

    def run_on_candles(self, candles: List[dict]) -> BacktestResult:
        start_ts = time.time()

        if len(candles) < self.warmup + 50:
            raise ValueError(f"not enough candles: {len(candles)}")

        start_iso = datetime.fromtimestamp(candles[0]["open_time"] / 1000, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(candles[-1]["open_time"] / 1000, tz=timezone.utc).isoformat()

        logger.info(
            f"BetaBacktester: running {len(candles)} candles | warmup={self.warmup} "
            f"| max_hold_bars={self.max_hold_bars}"
        )

        for i in range(self.warmup, len(candles)):
            self.candles_processed += 1

            start_idx = max(0, i - self.max_window)
            window = candles[start_idx:i]
            trigger_candle = candles[i]

            self.trader.process_candle(trigger_candle)

            regime_tag = self.tagger.tag(window)
            regime = regime_tag.regime

            signals = self.registry.run_all(window, regime=regime)
            actionable = [s for s in signals if s.direction in ("LONG", "SHORT")]
            if not actionable:
                self.rejected_hold += 1
                self.trades_rejected += 1
                continue

            self.debates_run += 1
            debate = self.debate.run(
                signals, window,
                symbol=self.symbol, timeframe=self.timeframe,
            )

            min_conf = self.registry.get_min_confidence(regime)
            passed_gate = debate.winner_confidence >= min_conf

            # D7c: record every debate for the histogram
            self._debate_records.append({
                "winner": debate.winner,
                "confidence": float(debate.winner_confidence),
                "min_conf": float(min_conf),
                "passed_gate": bool(passed_gate),
                "regime": regime,
            })

            if not passed_gate:
                self.rejected_low_confidence += 1
                self.trades_rejected += 1
                continue

            verdict = self.jury.run(
                debate=debate,
                candles=window,
                equity=self.trader.balance,
                portfolio_state={
                    "open_positions": len(self.trader.open_trades),
                    "current_exposure_pct": 0.0,
                    "daily_pnl_pct": 0.0,
                    "daily_trades": 0,
                    "consecutive_losses": 0,
                },
                mode=self.mode,
                account_type=self.account_type,
            )

            if verdict.final_decision != "APPROVED":
                if not verdict.risk.approved:
                    self.rejected_risk_jury += 1
                elif not verdict.portfolio.approved:
                    self.rejected_portfolio_jury += 1
                else:
                    self.rejected_risk_jury += 1
                self.trades_rejected += 1
                continue

            winner_dir = "LONG" if debate.winner == "BUY" else "SHORT" if debate.winner == "SELL" else None
            contributing = [s.strategy for s in actionable if s.direction == winner_dir] if winner_dir else []

            trade = self.trader.open_trade(
                verdict, [trigger_candle],
                max_hold_bars=self.max_hold_bars,
                contributing_strategies=contributing,
                regime=regime,
            )
            if trade:
                self.trades_opened += 1

        if self.trader.open_trades and len(candles) > 0:
            last = candles[-1]
            before = len(self.trader.closed_trades)
            self.trader.close_all_at_price(last)
            for t in self.trader.closed_trades[before:]:
                self.analyzer.record_trade(
                    contributing_strategies=list(t.contributing_strategies),
                    direction=t.direction,
                    pnl_usd=t.pnl_usd,
                    regime=t.regime,
                )

        runtime = time.time() - start_ts

        stats = self.trader.get_stats()
        trade_returns = []
        for t in self.trader.closed_trades:
            if t.entry_price > 0:
                notional = t.entry_price * t.qty
                trade_returns.append(t.pnl_usd / notional if notional > 0 else 0.0)

        try:
            t0 = candles[0]["open_time"] / 1000
            t1 = candles[-1]["open_time"] / 1000
            period_days = max((t1 - t0) / 86400.0, 1e-9)
        except Exception:
            period_days = None

        stats = enrich(stats, trade_returns, periods_per_year=None, period_days=period_days)
        stats["return_pct"] = round(
            (stats["ending_balance"] - stats["starting_balance"])
            / stats["starting_balance"] * 100, 2
        ) if stats["starting_balance"] > 0 else 0.0

        trades_out = [t.to_dict() for t in self.trader.closed_trades]

        logger.info(
            f"BetaBacktester done: trades={self.trades_opened} "
            f"rejected={self.trades_rejected} runtime={runtime:.1f}s"
        )

        return BacktestResult(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_iso=start_iso,
            end_iso=end_iso,
            total_candles=len(candles),
            warmup=self.warmup,
            runtime_sec=round(runtime, 2),
            stats=stats,
            trades=trades_out,
        )

    # ------------------------------------------------------------------
    # D7c diagnostics
    # ------------------------------------------------------------------

    def confidence_histogram(self) -> Dict[str, Any]:
        """Bucket winner_confidence for BUY/SELL winners.

        Only counts debates where the winner was BUY or SELL
        (HOLD verdicts never reach the gate).
        """
        buckets_all = {f"{CONF_BUCKETS[i]:.1f}-{CONF_BUCKETS[i+1]:.1f}": 0
                       for i in range(len(CONF_BUCKETS) - 1)}
        buckets_passed = dict(buckets_all)
        buckets_rejected = dict(buckets_all)

        n_total = 0
        n_passed = 0
        n_rejected = 0
        confs = []

        for r in self._debate_records:
            if r["winner"] not in ("BUY", "SELL"):
                continue
            c = r["confidence"]
            confs.append(c)
            n_total += 1
            label = None
            for i in range(len(CONF_BUCKETS) - 1):
                if CONF_BUCKETS[i] <= c < CONF_BUCKETS[i + 1]:
                    label = f"{CONF_BUCKETS[i]:.1f}-{CONF_BUCKETS[i+1]:.1f}"
                    break
            if label is None:
                label = f"{CONF_BUCKETS[-2]:.1f}-{CONF_BUCKETS[-1]:.1f}"

            buckets_all[label] += 1
            if r["passed_gate"]:
                buckets_passed[label] += 1
                n_passed += 1
            else:
                buckets_rejected[label] += 1
                n_rejected += 1

        mean_c = sum(confs) / len(confs) if confs else 0.0
        confs_sorted = sorted(confs)
        median_c = confs_sorted[len(confs_sorted) // 2] if confs_sorted else 0.0

        return {
            "n_buy_sell_debates": n_total,
            "n_passed_gate": n_passed,
            "n_rejected_by_gate": n_rejected,
            "mean_confidence": round(mean_c, 3),
            "median_confidence": round(median_c, 3),
            "buckets_all": buckets_all,
            "buckets_passed": buckets_passed,
            "buckets_rejected": buckets_rejected,
        }

    def volatile_by_strategy(self) -> Dict[str, Dict[str, Any]]:
        """Per-strategy trade count, wins, and PnL restricted to VOLATILE regime."""
        out: Dict[str, Dict[str, Any]] = {}
        for t in self.trader.closed_trades:
            if t.regime != "VOLATILE":
                continue
            for s in (t.contributing_strategies or []):
                e = out.setdefault(s, {"trades": 0, "wins": 0, "losses": 0,
                                       "pnl_usd": 0.0})
                e["trades"] += 1
                if t.pnl_usd > 0:
                    e["wins"] += 1
                elif t.pnl_usd < 0:
                    e["losses"] += 1
                e["pnl_usd"] += t.pnl_usd
        for s, e in out.items():
            e["pnl_usd"] = round(e["pnl_usd"], 2)
            e["win_rate"] = round(e["wins"] / e["trades"] * 100, 1) if e["trades"] else 0.0
        return out

    def tmo_by_strategy(self) -> Dict[str, Dict[str, Any]]:
        """Per-strategy trades + PnL + avg bars for CLOSED_TIMEOUT exits."""
        out: Dict[str, Dict[str, Any]] = {}
        for t in self.trader.closed_trades:
            if t.status != "CLOSED_TIMEOUT":
                continue
            for s in (t.contributing_strategies or []):
                e = out.setdefault(s, {"trades": 0, "wins": 0, "losses": 0,
                                       "pnl_usd": 0.0, "bars_total": 0})
                e["trades"] += 1
                if t.pnl_usd > 0:
                    e["wins"] += 1
                elif t.pnl_usd < 0:
                    e["losses"] += 1
                e["pnl_usd"] += t.pnl_usd
                e["bars_total"] += t.bars_held
        for s, e in out.items():
            e["pnl_usd"] = round(e["pnl_usd"], 2)
            e["avg_bars"] = round(e["bars_total"] / e["trades"], 1) if e["trades"] else 0.0
            del e["bars_total"]
            e["win_rate"] = round(e["wins"] / e["trades"] * 100, 1) if e["trades"] else 0.0
        return out

    def get_analyzer_dict(self) -> Dict[str, Any]:
        return self.analyzer.to_dict()

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "candles_processed": self.candles_processed,
            "debates_run": self.debates_run,
            "trades_opened": self.trades_opened,
            "trades_rejected": self.trades_rejected,
            "rejected_hold": self.rejected_hold,
            "rejected_low_confidence": self.rejected_low_confidence,
            "rejected_risk_jury": self.rejected_risk_jury,
            "rejected_portfolio_jury": self.rejected_portfolio_jury,
            "max_hold_bars_used": self.max_hold_bars,
            # D7c
            "confidence_histogram": self.confidence_histogram(),
            "volatile_by_strategy": self.volatile_by_strategy(),
            "tmo_by_strategy": self.tmo_by_strategy(),
        }