"""Beta Brain backtest CLI.

Usage:
    python scripts/backtest_beta.py
    python scripts/backtest_beta.py --symbol BTCUSDT --candles 10000
    python scripts/backtest_beta.py --symbol BTCUSDT --candles 3000 --warmup 100
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.beta_backtester import BetaBacktester
from backtest.reporter import build_full_report, write_report_files
from utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Beta Brain Backtest")
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timeframe", type=str, default="5m")
    parser.add_argument("--candles", type=int, default=10000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--account", type=str, default="personal")
    parser.add_argument("--config", type=str, default="config/beta_personal.yaml")
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--mode", type=str, default="scalp")
    args = parser.parse_args()

    logger.info("=" * 62)
    logger.info(f"  Beta Brain Backtest | {args.symbol} {args.timeframe}")
    logger.info(f"  Candles: {args.candles} | Warmup: {args.warmup} | Mode: {args.mode}")
    logger.info("=" * 62)

    bt = BetaBacktester(
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_type=args.account,
        config_path=args.config,
        starting_balance=args.starting_balance,
        warmup=args.warmup,
        mode=args.mode,
    )

    # Fetch candles
    logger.info(f"Fetching {args.candles} {args.timeframe} candles for {args.symbol}...")
    hist = asyncio.run(bt.fetch_candles(total=args.candles))
    candles = bt._to_beta_candles(hist)
    logger.info(f"Fetched {len(candles)} candles")

    # Run
    result = bt.run_on_candles(candles)
    analyzer_dict = bt.get_analyzer_dict()
    diag = bt.get_diagnostics()

    # Report
    report_text = build_full_report(result.to_dict(), analyzer_dict,
                                    args.symbol, args.timeframe)
    report_text += "\nDIAGNOSTICS\n" + "-" * 62 + "\n"
    for k, v in diag.items():
        report_text += f"  {k:<20} {v}\n"
    report_text += "=" * 62

    print("\n" + report_text + "\n")

    paths = write_report_files(
        report_text=report_text,
        result=result.to_dict(),
        analyzer_dict=analyzer_dict,
        trades=result.trades,
        symbol=args.symbol,
    )
    print(f"Report saved: {paths['txt']}")
    print(f"Data saved:   {paths['json']}")
    print(f"Trades saved: {paths['csv']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
