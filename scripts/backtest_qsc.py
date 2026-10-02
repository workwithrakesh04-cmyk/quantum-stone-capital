"""QSC backtest CLI.

Usage:
    python scripts/backtest_qsc.py
    python scripts/backtest_qsc.py --symbol BTCUSDT --candles 5000
    python scripts/backtest_qsc.py --symbol BTCUSDT --candles 20000

Mirrors scripts/backtest_beta.py. Uses the same reporter module
(backtest/reporter.py) so output files use the same naming scheme,
except with a `backtest_qsc_` prefix.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.qsc_backtester import QSCBacktester
from backtest.reporter import build_full_report, write_report_files
from utils.logger import logger


def _log_diagnostics(diag: dict) -> str:
    lines = ["\nDIAGNOSTICS", "-" * 62]
    for k, v in diag.items():
        lines.append(f"  {k:<28} {v}")
    lines.append("=" * 62)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="QSC Backtest")
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timeframe", type=str, default="5m")
    parser.add_argument("--candles", type=int, default=5000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--window-size", type=int, default=200)
    parser.add_argument("--max-hold-bars", type=int, default=12)
    parser.add_argument("--account", type=str, default="personal")
    parser.add_argument("--config", type=str, default="config/master.yaml")
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    args = parser.parse_args()

    logger.info("=" * 62)
    logger.info(f"  QSC Backtest | {args.symbol} {args.timeframe}")
    logger.info(f"  Candles: {args.candles} | Warmup: {args.warmup} | Window: {args.window_size}")
    logger.info(f"  Hybrid: DISABLED (D9b is QSC-only measurement)")
    logger.info("=" * 62)

    bt = QSCBacktester(
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_name=args.account,
        config_path=args.config,
        starting_balance=args.starting_balance,
        warmup=args.warmup,
        window_size=args.window_size,
        max_hold_bars=args.max_hold_bars,
    )

    logger.info(f"Fetching {args.candles} {args.timeframe} candles for {args.symbol}...")
    hist = asyncio.run(bt.fetch_candles(total=args.candles))
    candles = bt._to_beta_candles(hist)
    logger.info(f"Fetched {len(candles)} candles")

    result = bt.run_on_candles(candles)
    analyzer_dict = bt.get_analyzer_dict()
    diag = bt.get_diagnostics()

    report_text = build_full_report(result.to_dict(), analyzer_dict,
                                    args.symbol, args.timeframe)
    report_text += _log_diagnostics(diag)

    print("\n" + report_text + "\n")

    # Write report files with a `_qsc` suffix so they don't clash with
    # the Beta files in data/logs/
    paths = write_report_files(
        report_text=report_text,
        result=result.to_dict(),
        analyzer_dict=analyzer_dict,
        trades=result.trades,
        symbol=args.symbol,
        out_dir="data/logs",
    )
    # Rename with _qsc suffix
    for key in ("txt", "json", "csv"):
        old = Path(paths[key])
        if old.exists():
            new_name = old.name.replace("backtest_beta_", "backtest_qsc_")
            new = old.with_name(new_name)
            try:
                old.replace(new)
                paths[key] = str(new)
            except Exception:
                pass

    print(f"Report saved: {paths['txt']}")
    print(f"Data saved:   {paths['json']}")
    print(f"Trades saved: {paths['csv']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())