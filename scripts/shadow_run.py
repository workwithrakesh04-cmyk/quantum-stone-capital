"""D8 Shadow Runner.

Fetches the newest N candles from Binance (out-of-sample data beyond
the training window that D8c-3 was tuned on), runs the exact same
Beta Brain pipeline on each candle using the same window size, warmup,
max_hold_bars, and hard stop as the backtester, and writes every
decision to a JSONL log.

No real trades. No paper broker. Just the pipeline running on fresh
data with PaperTrader simulating fills locally.

Usage:
    python scripts/shadow_run.py
    python scripts/shadow_run.py --candles 100
    python scripts/shadow_run.py --candles 500 --window-hard-stop 3.0

Defaults chosen to match D8c-3 exactly:
    --window-size 500  --warmup 100  --max-hold-bars 12
    --window-hard-stop 3.0  --starting-balance 10000
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

from feeds.historical_loader import HistoricalLoader
from beta_brain.beta_brain import BetaBrain
from beta_brain.paper_trader import PaperTrader
from beta_brain.shadow_audit import ShadowAudit


TRAINING_WINDOW_END_MS = int(
    datetime.fromisoformat("2026-10-01T16:20:00+00:00").timestamp() * 1000
)


class ShadowRunner:
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "5m",
        n_new_candles: int = 100,
        seed_buffer: int = 500,
        warmup: int = 100,
        window_size: int = 500,
        max_hold_bars: int = 12,
        window_hard_stop_pct: float = 3.0,
        starting_balance: float = 10000.0,
        account_type: str = "personal",
        mode: str = "scalp",
        run_id: str | None = None,
        fresh: bool = True,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.n_new_candles = n_new_candles
        self.seed_buffer = seed_buffer
        self.warmup = warmup
        self.window_size = window_size
        self.max_hold_bars = max_hold_bars
        self.window_hard_stop_pct = window_hard_stop_pct
        self.starting_balance = starting_balance
        self.account_type = account_type
        self.mode = mode

        # Build a lightweight SymbolMapper to translate BTCUSDT -> BTCUSDT
        # (BetaBrain uses context.symbol as-is for the verdict)
        # D8 isolation: tag every record with run_id so multiple runs
        # in one day do not mix during analysis. Default fresh=True
        # clears today's active JSONL before starting.
        self.run_id = run_id or datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        self.audit = ShadowAudit()
        if fresh and self.audit.current_file is not None:
            try:
                self.audit.current_file.write_text("", encoding="utf-8")
                logger.info(
                    f"ShadowRunner: cleared {self.audit.current_file} "
                    f"(fresh run {self.run_id})"
                )
            except Exception as e:
                logger.warning(f"ShadowRunner: clear failed: {e}")

        self.brain = BetaBrain(timeframe=timeframe)
        self.trader = PaperTrader(
            account_type=account_type,
            starting_balance=starting_balance,
            on_trade_close=self._on_trade_close,
        )
        self._closed_trades_log: list = []
        self._window_halted = False
        self._halt_candle_idx: int | None = None
        self.stats = {
            "candles_processed": 0,
            "debates_run": 0,
            "verdicts_approved": 0,
            "verdicts_rejected": 0,
            "trades_opened": 0,
            "trades_closed": 0,
            "halted": False,
        }

    def _on_trade_close(self, pnl: float) -> None:
        if not self.trader.closed_trades:
            return
        t = self.trader.closed_trades[-1]
        self._closed_trades_log.append(t.to_dict())
        self.stats["trades_closed"] += 1

    async def fetch_candles(self) -> list:
        """Fetch enough candles to seed the window plus N new ones.

        We fetch newest `seed_buffer + n_new_candles` and slice the
        last `n_new_candles` as the actionable range. The first
        `seed_buffer` act as warmup context.
        """
        total = self.seed_buffer + self.n_new_candles
        loader = HistoricalLoader(symbol=self.symbol, use_cache=False)
        raw = await loader.fetch_klines(timeframe=self.timeframe, limit=total)
        return self._to_beta_candles(raw)

    def _to_beta_candles(self, raw: list) -> list:
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

    def _make_context(self, window: list, symbol: str):
        """Wrap a candle window as the MarketContext shape
        BetaBrain._context_to_candles expects."""
        return SimpleNamespace(
            symbol=symbol,
            closes=[c["close"] for c in window],
            highs=[c["high"] for c in window],
            lows=[c["low"] for c in window],
            opens=[c["open"] for c in window],
            volumes=[c["volume"] for c in window],
        )

    def _check_hard_stop(self, trigger_candle: dict, candle_idx: int) -> bool:
        """Returns True if the hard stop just fired this candle."""
        if self._window_halted or self.window_hard_stop_pct <= 0.0:
            return False
        if self.starting_balance <= 0:
            return False
        ret_pct = (
            (self.trader.balance - self.starting_balance)
            / self.starting_balance * 100.0
        )
        if ret_pct <= -self.window_hard_stop_pct:
            self.trader.close_all_at_price(trigger_candle)
            self._window_halted = True
            self._halt_candle_idx = candle_idx
            self.stats["halted"] = True
            logger.warning(
                f"ShadowRunner: HARD STOP at candle {candle_idx} "
                f"(ret={ret_pct:.2f}%)"
            )
            return True
        return False

    def run_on_candles(self, candles: list) -> dict:
        """Run the shadow loop over the last n_new_candles of `candles`.

        Requires len(candles) >= seed_buffer + n_new_candles.
        """
        if len(candles) < self.seed_buffer + self.n_new_candles:
            raise ValueError(
                f"need >= {self.seed_buffer + self.n_new_candles} candles; "
                f"got {len(candles)}"
            )

        start_idx = len(candles) - self.n_new_candles
        logger.info(
            f"ShadowRunner: starting at candle {start_idx} "
            f"(of {len(candles)}); seed={self.seed_buffer}, "
            f"new={self.n_new_candles}"
        )

        for i in range(start_idx, len(candles)):
            self.stats["candles_processed"] += 1
            trigger_candle = candles[i]

            # Process open trades first (SL/TP/TMO)
            self.trader.process_candle(trigger_candle)

            # Hard stop check
            if self._check_hard_stop(trigger_candle, i):
                self._log_decision(
                    candle_idx=i,
                    trigger_candle=trigger_candle,
                    verdict=None,
                    regime=None,
                    note="hard_stop",
                )
                continue
            if self._window_halted:
                # Close remaining open trades at this candle, log, skip
                self._log_decision(
                    candle_idx=i,
                    trigger_candle=trigger_candle,
                    verdict=None,
                    regime=None,
                    note="halted_skip",
                )
                continue

            # Build the window and run the Beta Brain
            window_start = max(0, i - self.window_size)
            window = candles[window_start:i]

            context = self._make_context(window, self.symbol)
            portfolio_state = {
                "open_positions": len(self.trader.open_trades),
                "current_exposure_pct": 0.0,
                "daily_pnl_pct": 0.0,
                "daily_trades": 0,
                "consecutive_losses": 0,
            }

            self.stats["debates_run"] += 1
            try:
                verdict = self.brain.run(
                    context,
                    account_type=self.account_type,
                    mode=self.mode,
                    equity=self.trader.balance,
                    portfolio_state=portfolio_state,
                )
            except Exception as e:
                logger.error(f"ShadowRunner: brain failed at candle {i}: {e}")
                verdict = None

            if verdict is None:
                self.stats["verdicts_rejected"] += 1
                self._log_decision(
                    candle_idx=i,
                    trigger_candle=trigger_candle,
                    verdict=None,
                    regime=None,
                    note="no_verdict",
                )
                continue

            # A verdict came back - either APPROVED or a jury rejection
            if verdict.final_decision != "APPROVED":
                self.stats["verdicts_rejected"] += 1
                self._log_decision(
                    candle_idx=i,
                    trigger_candle=trigger_candle,
                    verdict=verdict,
                    regime=None,
                    note="jury_rejected",
                )
                continue

            self.stats["verdicts_approved"] += 1

            # Open the trade
            trade = self.trader.open_trade(
                verdict,
                [trigger_candle],
                max_hold_bars=self.max_hold_bars,
                contributing_strategies=[],
                regime="SHADOW",
            )
            if trade:
                self.stats["trades_opened"] += 1

            self._log_decision(
                candle_idx=i,
                trigger_candle=trigger_candle,
                verdict=verdict,
                regime="SHADOW",
                note="opened",
                trade_id=trade.id if trade else None,
            )

        # End-of-run: close remaining trades
        if self.trader.open_trades:
            last = candles[-1]
            self.trader.close_all_at_price(last)

        # Return the enriched summary, not the raw counters
        return self.final_summary()

    def _log_decision(
        self,
        candle_idx: int,
        trigger_candle: dict,
        verdict,
        regime,
        note: str,
        trade_id: int | None = None,
    ) -> None:
        record = {
            "kind": "shadow_decision",
            "run_id": self.run_id,
            "candle_idx": candle_idx,
            "candle_open_time": int(trigger_candle.get("open_time", 0)),
            # D8 fidelity fix: log full OHLC so shadow_analysis can
            # faithfully replay intrabar SL/TP with PaperTrader.
            "candle_open": float(trigger_candle["open"]),
            "candle_high": float(trigger_candle["high"]),
            "candle_low": float(trigger_candle["low"]),
            "candle_close": float(trigger_candle["close"]),
            "note": note,
            "balance": round(self.trader.balance, 2),
            "open_trades": len(self.trader.open_trades),
            "trade_id": trade_id,
            "regime": regime,
        }
        if verdict is not None:
            record["verdict"] = verdict.to_dict()
        self.audit.write(record)

    def final_summary(self) -> dict:
        stats = dict(self.stats)
        stats["starting_balance"] = round(self.starting_balance, 2)
        stats["ending_balance"] = round(self.trader.balance, 2)
        stats["net_pnl"] = round(self.trader.balance - self.starting_balance, 2)
        stats["return_pct"] = round(
            (self.trader.balance - self.starting_balance)
            / self.starting_balance * 100.0,
            2,
        ) if self.starting_balance > 0 else 0.0
        stats["run_id"] = self.run_id
        stats["halt_candle_idx"] = self._halt_candle_idx
        stats["max_hold_bars_used"] = self.max_hold_bars
        stats["window_hard_stop_pct"] = self.window_hard_stop_pct
        stats["closed_trades"] = self._closed_trades_log
        return stats


def _log_summary(stats: dict) -> None:
    logger.info("=" * 78)
    logger.info("SHADOW RUN SUMMARY")
    logger.info("=" * 78)
    logger.info(f"  candles_processed:    {stats['candles_processed']}")
    logger.info(f"  debates_run:          {stats['debates_run']}")
    logger.info(f"  verdicts_approved:    {stats['verdicts_approved']}")
    logger.info(f"  verdicts_rejected:    {stats['verdicts_rejected']}")
    logger.info(f"  trades_opened:        {stats['trades_opened']}")
    logger.info(f"  trades_closed:        {stats['trades_closed']}")
    logger.info(f"  halted:               {stats['halted']}")
    logger.info(f"  starting_balance:     ${stats['starting_balance']:.2f}")
    logger.info(f"  ending_balance:       ${stats['ending_balance']:.2f}")
    logger.info(f"  net_pnl:              ${stats['net_pnl']:+.2f}")
    logger.info(f"  return_pct:           {stats['return_pct']:+.2f}%")
    logger.info("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="D8 Shadow Runner")
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timeframe", type=str, default="5m")
    parser.add_argument("--candles", type=int, default=100,
                        help="Number of NEW (out-of-sample) candles to run")
    parser.add_argument("--seed-buffer", type=int, default=500,
                        help="Candles of history before the first NEW candle")
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--window-size", type=int, default=500)
    parser.add_argument("--max-hold-bars", type=int, default=12)
    parser.add_argument("--window-hard-stop", type=float, default=3.0,
                        help="Halt trading if return hits -X% (0 = disabled)")
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--account", type=str, default="personal")
    parser.add_argument("--mode", type=str, default="scalp")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Tag for this run (default: UTC timestamp). "
                             "Records with different run_ids are kept "
                             "separate during analysis.")
    parser.add_argument("--append", action="store_true",
                        help="Do NOT clear today's JSONL before running. "
                             "Default is a fresh run.")
    args = parser.parse_args()

    runner = ShadowRunner(
        symbol=args.symbol,
        timeframe=args.timeframe,
        n_new_candles=args.candles,
        seed_buffer=args.seed_buffer,
        warmup=args.warmup,
        window_size=args.window_size,
        max_hold_bars=args.max_hold_bars,
        window_hard_stop_pct=args.window_hard_stop,
        starting_balance=args.starting_balance,
        account_type=args.account,
        mode=args.mode,
        run_id=args.run_id,
        fresh=(not args.append),
    )

    logger.info("=" * 78)
    logger.info(f"  D8 Shadow Run | {args.symbol} {args.timeframe}")
    logger.info(f"  NEW candles: {args.candles} | seed: {args.seed_buffer}")
    logger.info(f"  window_size: {args.window_size} | max_hold_bars: {args.max_hold_bars}")
    logger.info(f"  hard stop: {args.window_hard_stop}%")
    logger.info(f"  audit log: {runner.audit.current_file}")
    logger.info("=" * 78)

    candles = asyncio.run(runner.fetch_candles())
    logger.info(f"Fetched {len(candles)} candles total "
                f"(seed + new)")

    # Report the OOS boundary
    if candles:
        first_new = candles[runner.seed_buffer] if len(candles) > runner.seed_buffer else candles[0]
        last = candles[-1]
        def _iso(ms):
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
        logger.info(f"  First NEW candle: {_iso(first_new['open_time'])}")
        logger.info(f"  Last candle:      {_iso(last['open_time'])}")
        logger.info(
            f"  Candles past training end (2026-10-01T16:20Z): "
            f"{sum(1 for c in candles if c['open_time'] > TRAINING_WINDOW_END_MS)}"
        )

    t0 = time.time()
    runner.run_on_candles(candles)
    runtime = time.time() - t0

    # final_summary() enriches the raw counters with balances,
    # net_pnl, return_pct, halt info, and the closed-trades list.
    stats = runner.final_summary()

    _log_summary(stats)
    logger.info(f"  runtime: {runtime:.1f}s")

    # Save a summary JSON for the analysis pass
    out_dir = Path("data/logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    summary_path = out_dir / f"shadow_run_{args.symbol}_{stamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)
    logger.info(f"  summary: {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())