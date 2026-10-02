"""QSC Backtester - historical simulation of MainBrainV2.

Mirrors BetaBacktester's shape but drives QSC's pipeline
(MainBrainV2.run) instead of BetaBrain.run.

Hybrid note: MainBrainV2 loads Beta Brain + ConsensusArbiter at
__init__ if config/consensus.yaml has beta.enabled=true. For a
QSC-only measurement we immediately null those two attributes
after construction. This does NOT modify MainBrainV2; it just
does not use two of its optional collaborators.

D9b is measurement-only. No config changes, no tuning.
"""
import asyncio
import time
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from loguru import logger

from feeds.historical_loader import HistoricalLoader
from core.main_brain_v2 import MainBrainV2
from backtest.qsc_context import build_market_context
from beta_brain.paper_trader import PaperTrader
from beta_brain.strategy_analyzer import StrategyAnalyzer
from beta_brain.performance_metrics import enrich


@dataclass
class QSCBacktestResult:
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


class QSCBacktester:
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "5m",
        account_name: str = "personal",
        config_path: str = "config/master.yaml",
        starting_balance: float = 10000.0,
        warmup: int = 100,
        window_size: int = 200,
        max_hold_bars: int = 12,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.account_name = account_name
        self.starting_balance = starting_balance
        self.warmup = warmup
        self.window_size = window_size
        self.max_hold_bars = max_hold_bars

        with open(config_path, "r", encoding="utf-8-sig") as f:
            self.master_cfg = yaml.safe_load(f)

        self.brain = MainBrainV2(config_path=config_path)
        # D9b: disable the hybrid for QSC-only measurement.
        # We do NOT modify main_brain_v2.py; we simply null the
        # two optional collaborators that __init__ set up.
        self._hybrid_was_enabled = (
            self.brain._beta is not None or self.brain._arbiter is not None
        )
        self.brain._beta = None
        self.brain._arbiter = None

        self.analyzer = StrategyAnalyzer()
        self.trader = PaperTrader(
            account_type=account_name,
            starting_balance=starting_balance,
            on_trade_close=self._on_trade_close,
        )

        # Counters
        self.candles_processed = 0
        self.contexts_built = 0
        self.brain_runs = 0
        self.pipeline_trades = 0
        self.pipeline_holds = 0
        self.trades_opened = 0

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

    def _to_beta_candles(self, raw: List[dict]) -> List[dict]:
        out = []
        for c in raw:
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

    def _open_qsc_trade(self, result, context, candle) -> bool:
        """Bridge a QSC PipelineResult into PaperTrader.open_trade.

        PaperTrader expects an object with `.final_decision`,
        `.ts`, `.symbol`, `.mode`, `.debate_winner`, and `.risk`
        (with position_size_qty, stop_loss_price, take_profit_price,
        risk_amount_usd).

        We synthesise that shape from the PipelineResult.
        """
        from types import SimpleNamespace

        entry = float(result.entry_price or candle["close"])
        sl = float(result.stop_loss or entry * 0.99)
        tp = float(result.take_profit or entry * 1.02)
        size = float(result.position_size or 0.0)
        if size <= 0.0:
            return False

        # Direction: QSC uses "long" / "short"; PaperTrader uses
        # "BUY" / "SELL" for the debate_winner field.
        d = (result.direction or "").lower()
        if d == "long":
            winner = "BUY"
        elif d == "short":
            winner = "SELL"
            # QSC's PipelineResult produces direction-agnostic SL/TP:
            #   stop_loss   = min(lows[-10:]) * 0.999   (below entry)
            #   take_profit = max(highs[-10:]) * 1.001  (above entry)
            # These are LONG-oriented. For a SHORT the stop must be
            # ABOVE entry and the target BELOW - so we swap them here.
            # D9b bug: without this swap, every short "stops out" at a
            # price below entry and books a guaranteed fake profit.
            sl, tp = tp, sl
        else:
            return False

        risk_per_unit = abs(entry - sl)
        risk_amount = risk_per_unit * size if risk_per_unit > 0 else 0.0

        risk = SimpleNamespace(
            position_size_qty=size,
            stop_loss_price=sl,
            take_profit_price=tp,
            risk_amount_usd=risk_amount,
        )
        verdict = SimpleNamespace(
            final_decision="APPROVED",
            ts=int(candle.get("open_time", 0)),
            symbol=self.symbol,
            mode="scalp",
            debate_winner=winner,
            risk=risk,
        )
        trade = self.trader.open_trade(
            verdict,
            [candle],
            max_hold_bars=self.max_hold_bars,
            contributing_strategies=[result.strategy_name or "qsc"],
            regime=(context.regime or "unknown").upper(),
        )
        return trade is not None

    def run_on_candles(self, candles: List[dict]) -> QSCBacktestResult:
        start_ts = time.time()

        if len(candles) < self.warmup + 50:
            raise ValueError(f"not enough candles: {len(candles)}")

        start_iso = datetime.fromtimestamp(
            candles[0]["open_time"] / 1000, tz=timezone.utc
        ).isoformat()
        end_iso = datetime.fromtimestamp(
            candles[-1]["open_time"] / 1000, tz=timezone.utc
        ).isoformat()

        logger.info(
            f"QSCBacktester: running {len(candles)} candles | warmup={self.warmup} "
            f"| window={self.window_size} | hybrid_disabled={self._hybrid_was_enabled}"
        )

        for i in range(self.warmup, len(candles)):
            self.candles_processed += 1
            trigger_candle = candles[i]

            # Process open trades on this candle first
            self.trader.process_candle(trigger_candle)

            # Build window + context
            start_idx = max(0, i - self.window_size)
            window = candles[start_idx:i]
            ctx = build_market_context(window, self.symbol, self.timeframe)
            if ctx is None:
                continue
            self.contexts_built += 1

            # Run QSC
            self.brain_runs += 1
            try:
                result = self.brain.run(ctx, account_name=self.account_name)
            except Exception as e:
                logger.error(f"QSCBacktester: brain.run failed at candle {i}: {e}")
                continue

            if result is None or not getattr(result, "is_trade", False):
                self.pipeline_holds += 1
                continue

            self.pipeline_trades += 1
            if self._open_qsc_trade(result, ctx, trigger_candle):
                self.trades_opened += 1

        # Close remaining trades at last candle
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

        # Stats + metrics (same enrich() the Beta backtester uses)
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
            / stats["starting_balance"] * 100.0, 2
        ) if stats["starting_balance"] > 0 else 0.0

        trades_out = [t.to_dict() for t in self.trader.closed_trades]

        logger.info(
            f"QSCBacktester done: brain_runs={self.brain_runs} "
            f"pipeline_trades={self.pipeline_trades} "
            f"trades_opened={self.trades_opened} runtime={runtime:.1f}s"
        )

        return QSCBacktestResult(
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

    def get_analyzer_dict(self) -> Dict[str, Any]:
        return self.analyzer.to_dict()

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "candles_processed": self.candles_processed,
            "contexts_built": self.contexts_built,
            "brain_runs": self.brain_runs,
            "pipeline_trades": self.pipeline_trades,
            "pipeline_holds": self.pipeline_holds,
            "trades_opened": self.trades_opened,
            "hybrid_was_enabled": self._hybrid_was_enabled,
            "max_hold_bars_used": self.max_hold_bars,
        }