"""Walk-Forward Backtest CLI for Beta Brain.

Usage:
    python scripts/walk_forward_beta.py
    python scripts/walk_forward_beta.py --symbol BTCUSDT --candles 20000 --windows 10
    python scripts/walk_forward_beta.py --candles 5000 --windows 2    (smoke test)

Default parameters produce 10 overlapping windows of 3500 candles each,
stepped by 1500, over a 20,000-candle BTCUSDT 5m series. This mirrors
the D7b single-run window (same 70-day period) but sliced into windows
for consistency analysis.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.walk_forward_beta import WalkForwardRunner
from utils.logger import logger


def _fmt(v, nd=2):
    if isinstance(v, (int, float)):
        return f"{v:.{nd}f}"
    return str(v)


def format_report(wf) -> str:
    agg = wf.aggregate
    pws = agg.get("per_window_summary", {})
    chained = agg.get("chained", {})

    lines = []
    lines.append("=" * 78)
    lines.append(f"BETA BRAIN WALK-FORWARD - {wf.symbol} {wf.timeframe}")
    lines.append("=" * 78)
    lines.append(f"Windows:        {wf.n_windows} (size={wf.window_size}, step={wf.step_size}, warmup={wf.warmup})")
    lines.append(f"Total candles:  {wf.total_candles}")
    lines.append(f"Runtime:        {wf.runtime_sec:.1f}s")
    lines.append("")

    lines.append("------------------- PER-WINDOW -------------------")
    lines.append(f"{'#':>3} {'Trades':>7} {'WR%':>7} {'PnL$':>10} {'Ret%':>8} {'DD%':>7} {'Sharpe':>8} {'Sortino':>8} {'Calmar':>8}")
    lines.append("-" * 78)
    for w in wf.windows:
        s = w.stats
        lines.append(
            f"{w.index + 1:>3} {s.get('total_trades', 0):>7} "
            f"{s.get('win_rate', 0):>6.1f}% "
            f"{s.get('net_pnl', 0):>+10.2f} "
            f"{s.get('return_pct', 0):>+7.2f}% "
            f"{s.get('max_drawdown_pct', 0):>6.2f}% "
            f"{s.get('sharpe', 0):>+8.2f} "
            f"{s.get('sortino', 0):>+8.2f} "
            f"{s.get('calmar', 0):>+8.2f}"
        )
    lines.append("")

    lines.append("------------------- AGGREGATE -------------------")
    lines.append(f"Sharpe   mean / median:  {_fmt(pws.get('sharpe_mean'))} / {_fmt(pws.get('sharpe_median'))}")
    lines.append(f"Sharpe   min / max:      {_fmt(pws.get('sharpe_min'))} / {_fmt(pws.get('sharpe_max'))}")
    lines.append(f"Sharpe   positive wins:  {pws.get('sharpe_positive_windows')}/{pws.get('n_windows')}")
    lines.append(f"Return%  mean:           {_fmt(pws.get('return_pct_mean'))}")
    lines.append(f"Return%  positive wins:  {pws.get('return_pct_positive_windows')}/{pws.get('n_windows')}")
    lines.append(f"DD%      mean / max:     {_fmt(pws.get('dd_pct_mean'))} / {_fmt(pws.get('dd_pct_max'))}")
    lines.append(f"WR%      mean:           {_fmt(pws.get('wr_mean'))}")
    lines.append(f"PF       mean:           {_fmt(pws.get('pf_mean'))}")
    lines.append(f"Trades   mean / total:   {_fmt(pws.get('trades_mean'))} / {pws.get('trades_total')}")
    lines.append("")

    lines.append("------------------- CHAINED EQUITY -------------------")
    lines.append(f"Starting:        ${chained.get('starting_balance', 0):.2f}")
    lines.append(f"Ending:          ${chained.get('ending_balance', 0):.2f}")
    lines.append(f"Net PnL:         ${chained.get('net_pnl', 0):+.2f}")
    lines.append(f"Return:          {chained.get('return_pct', 0):+.2f}%")
    lines.append(f"Curve:           " + " -> ".join(f"${v:.0f}" for v in (chained.get('curve') or [])))
    lines.append("")

    lines.append("------------------- PER-STRATEGY CONSISTENCY -------------------")
    lines.append(f"{'Strategy':<22} {'Wins':>6} {'Win%':>7} {'Trades':>7} {'TotalPnL':>11}")
    lines.append("-" * 78)
    strats = agg.get("per_strategy", {})
    rows = sorted(strats.items(), key=lambda kv: -kv[1].get("total_pnl", 0))
    for name, rec in rows:
        lines.append(
            f"{name:<22} {rec.get('windows_positive', 0):>6} "
            f"{rec.get('positive_rate', 0):>6.1f}% "
            f"{rec.get('total_trades', 0):>7} "
            f"{rec.get('total_pnl', 0):>+11.2f}"
        )
    lines.append("")

    lines.append("------------------- PER-REGIME CONSISTENCY -------------------")
    lines.append(f"{'Regime':<18} {'Wins':>6} {'Win%':>7} {'Trades':>7} {'TotalPnL':>11}")
    lines.append("-" * 78)
    regimes = agg.get("per_regime", {})
    rows = sorted(regimes.items(), key=lambda kv: -kv[1].get("total_pnl", 0))
    for name, rec in rows:
        lines.append(
            f"{name:<18} {rec.get('windows_positive', 0):>6} "
            f"{rec.get('positive_rate', 0):>6.1f}% "
            f"{rec.get('total_trades', 0):>7} "
            f"{rec.get('total_pnl', 0):>+11.2f}"
        )
    lines.append("")

    lines.append("=" * 78)
    return "\n".join(lines)


def write_outputs(wf, report_text: str) -> dict:
    out_dir = Path("data/logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    base = f"walk_forward_beta_{wf.symbol}_{stamp}"
    txt_path = out_dir / f"{base}.txt"
    json_path = out_dir / f"{base}.json"
    csv_path = out_dir / f"{base}_windows.csv"

    txt_path.write_text(report_text, encoding="utf-8")

    payload = wf.to_dict()
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # Per-window summary CSV
    headers = ["index", "start_iso", "end_iso", "n_candles",
               "total_trades", "wins", "losses", "win_rate",
               "net_pnl", "return_pct", "max_drawdown_pct",
               "sharpe", "sortino", "calmar"]
    rows = [",".join(headers)]
    for w in wf.windows:
        s = w.stats
        row = [
            str(w.index),
            w.start_iso,
            w.end_iso,
            str(w.n_candles),
            str(s.get("total_trades", 0)),
            str(s.get("wins", 0)),
            str(s.get("losses", 0)),
            str(s.get("win_rate", 0)),
            str(s.get("net_pnl", 0)),
            str(s.get("return_pct", 0)),
            str(s.get("max_drawdown_pct", 0)),
            str(s.get("sharpe", 0)),
            str(s.get("sortino", 0)),
            str(s.get("calmar", 0)),
        ]
        rows.append(",".join(row))
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    return {"txt": str(txt_path), "json": str(json_path), "csv": str(csv_path)}


def main():
    parser = argparse.ArgumentParser(description="Beta Brain Walk-Forward")
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timeframe", type=str, default="5m")
    parser.add_argument("--candles", type=int, default=20000)
    parser.add_argument("--windows", type=int, default=10)
    parser.add_argument("--window-size", type=int, default=3500)
    parser.add_argument("--step", type=int, default=1500)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--account", type=str, default="personal")
    parser.add_argument("--config", type=str, default="config/beta_personal.yaml")
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--mode", type=str, default="scalp")
    parser.add_argument(
        "--window-hard-stop",
        type=float,
        default=0.0,
        help="If >0, halt trading for the rest of a window when its "
             "cumulative return hits -X%%. Example: 3.0 = halt at -3%%.",
    )
    args = parser.parse_args()

    runner = WalkForwardRunner(
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_type=args.account,
        config_path=args.config,
        starting_balance=args.starting_balance,
        n_windows=args.windows,
        window_size=args.window_size,
        step_size=args.step,
        warmup=args.warmup,
        mode=args.mode,
        window_hard_stop_pct=args.window_hard_stop,
    )

    logger.info("=" * 78)
    logger.info(f"  Walk-Forward | {args.symbol} {args.timeframe}")
    logger.info(f"  Candles: {args.candles} | Windows: {args.windows} | "
                f"Window size: {args.window_size} | Step: {args.step}")
    logger.info(f"  Window hard stop: {args.window_hard_stop}%")
    logger.info(f"  Need >= {runner.required_candles} candles")
    logger.info("=" * 78)

    candles = asyncio.run(runner.fetch_candles(total=args.candles))
    logger.info(f"Fetched {len(candles)} candles")

    wf = asyncio.run(runner.run(candles=candles))

    report_text = format_report(wf)
    print("\n" + report_text + "\n")

    paths = write_outputs(wf, report_text)
    print(f"Report saved: {paths['txt']}")
    print(f"Data saved:   {paths['json']}")
    print(f"Windows CSV:  {paths['csv']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())