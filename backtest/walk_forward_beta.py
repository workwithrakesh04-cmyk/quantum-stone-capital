"""Walk-Forward Runner for Beta Brain.

Slices a candle series into N overlapping windows, runs the existing
BetaBacktester on each window independently, and aggregates the results.

D8b scope:
  - No config changes
  - No changes to BetaBacktester
  - Fresh BetaBacktester instance per window (no state carryover)
  - Per-window metrics + chained equity + per-strategy and per-regime
    consistency across windows

Window semantics:
  - Each window is `window_size` candles long, stepped by `step_size`
  - Each window carries `warmup` candles of pre-roll from BEFORE its
    start index (so strategies have history to work with). Trades are
    only counted when they open inside the window's own bar range.
  - Trades are attributed to the window they OPENED in.
"""
import asyncio
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from loguru import logger

from backtest.beta_backtester import BetaBacktester


@dataclass
class WindowResult:
    index: int
    start_idx: int
    end_idx: int
    start_iso: str
    end_iso: str
    n_candles: int
    runtime_sec: float
    stats: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WalkForwardResult:
    symbol: str
    timeframe: str
    n_windows: int
    window_size: int
    step_size: int
    warmup: int
    total_candles: int
    runtime_sec: float
    windows: List[WindowResult] = field(default_factory=list)
    aggregate: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


class WalkForwardRunner:
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "5m",
        account_type: str = "personal",
        config_path: str = "config/beta_personal.yaml",
        regime_filters_path: str = "config/strategy_regime_filters.yaml",
        tiers_path: str = "config/strategy_tiers.yaml",
        starting_balance: float = 10000.0,
        n_windows: int = 10,
        window_size: int = 3500,
        step_size: int = 1500,
        warmup: int = 100,
        max_window: int = 500,
        mode: str = "scalp",
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.account_type = account_type
        self.config_path = config_path
        self.regime_filters_path = regime_filters_path
        self.tiers_path = tiers_path
        self.starting_balance = starting_balance
        self.n_windows = n_windows
        self.window_size = window_size
        self.step_size = step_size
        self.warmup = warmup
        self.max_window = max_window
        self.mode = mode

        # Sanity: windows must fit
        required = warmup + (n_windows - 1) * step_size + window_size
        self.required_candles = required

    # ------------------------------------------------------------------
    # Window planning
    # ------------------------------------------------------------------

    def plan_windows(self, total_candles: int) -> List[Dict[str, int]]:
        """Return list of {window_start, window_end, slice_start}.

        window_start/end are indices into the candle list - the bar
        range of the window itself. slice_start includes the warmup
        pre-roll and is what we actually pass to BetaBacktester.
        """
        if total_candles < self.required_candles:
            raise ValueError(
                f"WalkForwardRunner: need >= {self.required_candles} candles "
                f"for {self.n_windows} windows of size {self.window_size} "
                f"stepped by {self.step_size} (warmup={self.warmup}); "
                f"got {total_candles}"
            )
        out = []
        for i in range(self.n_windows):
            window_start = self.warmup + i * self.step_size
            window_end = window_start + self.window_size
            slice_start = max(0, window_start - self.warmup)
            out.append({
                "index": i,
                "window_start": window_start,
                "window_end": window_end,
                "slice_start": slice_start,
            })
        return out

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def fetch_candles(self, total: int) -> List[dict]:
        """Fetch candles once using an ephemeral BetaBacktester.

        Uses the same cache path as scripts/backtest_beta.py.
        """
        probe = BetaBacktester(
            symbol=self.symbol,
            timeframe=self.timeframe,
            account_type=self.account_type,
            config_path=self.config_path,
            regime_filters_path=self.regime_filters_path,
            tiers_path=self.tiers_path,
            starting_balance=self.starting_balance,
            warmup=self.warmup,
            max_window=self.max_window,
            mode=self.mode,
        )
        hist = await probe.fetch_candles(total=total)
        return probe._to_beta_candles(hist)

    def _run_one_window(
        self,
        window_idx: int,
        candles_slice: List[dict],
        window_start_idx: int,
        window_end_idx: int,
    ) -> WindowResult:
        """Run a single window with a fresh BetaBacktester."""
        bt = BetaBacktester(
            symbol=self.symbol,
            timeframe=self.timeframe,
            account_type=self.account_type,
            config_path=self.config_path,
            regime_filters_path=self.regime_filters_path,
            tiers_path=self.tiers_path,
            starting_balance=self.starting_balance,
            warmup=self.warmup,
            max_window=self.max_window,
            mode=self.mode,
        )
        t0 = time.time()
        result = bt.run_on_candles(candles_slice)
        runtime = time.time() - t0

        # Re-fetch trades + diagnostics from the same bt instance.
        trades = result.trades
        diag = bt.get_diagnostics()

        return WindowResult(
            index=window_idx,
            start_idx=window_start_idx,
            end_idx=window_end_idx,
            start_iso=result.start_iso,
            end_iso=result.end_iso,
            n_candles=len(candles_slice),
            runtime_sec=round(runtime, 2),
            stats=result.stats,
            trades=trades,
            diagnostics=diag,
        )

    async def run(self, candles: Optional[List[dict]] = None) -> WalkForwardResult:
        start_ts = time.time()

        if candles is None:
            candles = await self.fetch_candles(total=self.required_candles)

        total_candles = len(candles)
        plans = self.plan_windows(total_candles)

        logger.info(
            f"WalkForwardRunner: {len(plans)} windows, size={self.window_size}, "
            f"step={self.step_size}, warmup={self.warmup}, "
            f"total_candles={total_candles}"
        )

        window_results: List[WindowResult] = []
        for p in plans:
            slice_ = candles[p["slice_start"]:p["window_end"]]
            logger.info(
                f"WalkForwardRunner: window {p['index'] + 1}/{len(plans)} "
                f"slice=[{p['slice_start']}:{p['window_end']}] "
                f"({len(slice_)} candles)"
            )
            wr = self._run_one_window(
                window_idx=p["index"],
                candles_slice=slice_,
                window_start_idx=p["window_start"],
                window_end_idx=p["window_end"],
            )
            window_results.append(wr)

        runtime = time.time() - start_ts
        aggregate = self.aggregate(window_results)

        return WalkForwardResult(
            symbol=self.symbol,
            timeframe=self.timeframe,
            n_windows=len(window_results),
            window_size=self.window_size,
            step_size=self.step_size,
            warmup=self.warmup,
            total_candles=total_candles,
            runtime_sec=round(runtime, 2),
            windows=window_results,
            aggregate=aggregate,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate(self, windows: List[WindowResult]) -> Dict[str, Any]:
        """Compute cross-window aggregate statistics."""
        n = len(windows)
        if n == 0:
            return {}

        # --- Per-window scalar summary ---
        sharpes = [w.stats.get("sharpe", 0.0) for w in windows]
        sortinos = [w.stats.get("sortino", 0.0) for w in windows]
        calmars = [w.stats.get("calmar", 0.0) for w in windows]
        returns_pct = [w.stats.get("return_pct", 0.0) for w in windows]
        dds_pct = [w.stats.get("max_drawdown_pct", 0.0) for w in windows]
        trade_counts = [w.stats.get("total_trades", 0) for w in windows]
        wrs = [w.stats.get("win_rate", 0.0) for w in windows]
        pfs = []
        for w in windows:
            pf = w.stats.get("profit_factor", 0)
            pfs.append(pf if isinstance(pf, (int, float)) else float("inf"))

        def _safe_mean(xs):
            xs = [x for x in xs if x is not None]
            return round(sum(xs) / len(xs), 4) if xs else 0.0

        def _safe_median(xs):
            xs = sorted(x for x in xs if x is not None)
            if not xs:
                return 0.0
            m = len(xs) // 2
            if len(xs) % 2:
                return round(xs[m], 4)
            return round((xs[m - 1] + xs[m]) / 2, 4)

        per_window_summary = {
            # NOTE (D8c): sharpe_mean can be badly distorted by windows with
            # very few trades (small-sample artifact). sharpe_median is the
            # more reliable cross-window statistic. Prefer median.
            "sharpe_mean": _safe_mean(sharpes),
            "sharpe_median": _safe_median(sharpes),
            "sharpe_min": round(min(sharpes), 4) if sharpes else 0.0,
            "sharpe_max": round(max(sharpes), 4) if sharpes else 0.0,
            "sharpe_positive_windows": sum(1 for s in sharpes if s > 0),
            "sortino_mean": _safe_mean(sortinos),
            "calmar_mean": _safe_mean(calmars),
            "return_pct_mean": _safe_mean(returns_pct),
            "return_pct_positive_windows": sum(1 for r in returns_pct if r > 0),
            "dd_pct_mean": _safe_mean(dds_pct),
            "dd_pct_max": round(max(dds_pct), 4) if dds_pct else 0.0,
            "trades_mean": round(_safe_mean(trade_counts), 2),
            "trades_total": sum(trade_counts),
            "wr_mean": _safe_mean(wrs),
            "pf_mean": _safe_mean(pfs),
            "n_windows": n,
        }

        # --- Chained equity (compound each window's return_pct in order) ---
        chained = self.starting_balance
        chained_curve = [round(chained, 2)]
        for w in windows:
            r = w.stats.get("return_pct", 0.0) / 100.0
            chained = chained * (1.0 + r)
            chained_curve.append(round(chained, 2))

        chained_summary = {
            "starting_balance": round(self.starting_balance, 2),
            "ending_balance": round(chained, 2),
            "net_pnl": round(chained - self.starting_balance, 2),
            "return_pct": round((chained / self.starting_balance - 1.0) * 100.0, 2),
            "curve": chained_curve,
        }

        # --- Per-strategy consistency ---
        strat_windows: Dict[str, Dict[str, Any]] = {}
        for w in windows:
            seen_this_window = set()
            for t in w.trades:
                for s in (t.get("contributing_strategies") or []):
                    if s in seen_this_window:
                        continue
                    seen_this_window.add(s)
                    e = strat_windows.setdefault(
                        s, {"windows_present": 0, "windows_positive": 0,
                            "windows_negative": 0, "total_pnl": 0.0,
                            "total_trades": 0}
                    )
                    e["windows_present"] += 1
            # Now attribute pnl per strategy per window
            pnl_per_strat_this_window: Dict[str, float] = {}
            for t in w.trades:
                for s in (t.get("contributing_strategies") or []):
                    pnl_per_strat_this_window[s] = (
                        pnl_per_strat_this_window.get(s, 0.0) + t.get("pnl_usd", 0.0)
                    )
                    strat_windows[s]["total_trades"] += 1
            for s, pnl in pnl_per_strat_this_window.items():
                strat_windows[s]["total_pnl"] += pnl
                if pnl > 0:
                    strat_windows[s]["windows_positive"] += 1
                elif pnl < 0:
                    strat_windows[s]["windows_negative"] += 1

        for s, e in strat_windows.items():
            e["total_pnl"] = round(e["total_pnl"], 2)
            wp = e["windows_positive"]
            wn = e["windows_negative"]
            tot = wp + wn
            e["positive_rate"] = round(wp / tot * 100, 1) if tot else 0.0

        # --- Per-regime consistency ---
        regime_windows: Dict[str, Dict[str, Any]] = {}
        for w in windows:
            pnl_per_regime_this_window: Dict[str, float] = {}
            trades_per_regime_this_window: Dict[str, int] = {}
            for t in w.trades:
                r = t.get("regime", "") or "UNKNOWN"
                pnl_per_regime_this_window[r] = (
                    pnl_per_regime_this_window.get(r, 0.0) + t.get("pnl_usd", 0.0)
                )
                trades_per_regime_this_window[r] = trades_per_regime_this_window.get(r, 0) + 1
            for r, pnl in pnl_per_regime_this_window.items():
                e = regime_windows.setdefault(
                    r, {"windows_present": 0, "windows_positive": 0,
                        "windows_negative": 0, "total_pnl": 0.0,
                        "total_trades": 0}
                )
                e["windows_present"] += 1
                e["total_pnl"] += pnl
                e["total_trades"] += trades_per_regime_this_window[r]
                if pnl > 0:
                    e["windows_positive"] += 1
                elif pnl < 0:
                    e["windows_negative"] += 1

        for r, e in regime_windows.items():
            e["total_pnl"] = round(e["total_pnl"], 2)
            wp = e["windows_positive"]
            wn = e["windows_negative"]
            tot = wp + wn
            e["positive_rate"] = round(wp / tot * 100, 1) if tot else 0.0

        return {
            "per_window_summary": per_window_summary,
            "chained": chained_summary,
            "per_strategy": strat_windows,
            "per_regime": regime_windows,
        }