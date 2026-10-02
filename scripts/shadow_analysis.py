"""D8 Shadow Analysis CLI - thin wrapper around backtest.shadow_analysis.

Usage:
    python scripts/shadow_analysis.py
    python scripts/shadow_analysis.py --day 2026-10-02

Reads logs/shadow/YYYY-MM-DD.jsonl (or newest active day), replays
the trades through a fresh PaperTrader using logged OHLC, and prints
a side-by-side comparison against D8c-3 (in-sample).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.shadow_analysis import (
    load_shadow_day,
    load_shadow_newest,
    list_runs,
    replay_trades,
    compute_metrics,
    print_comparison,
)


def main():
    parser = argparse.ArgumentParser(description="D8 Shadow Analysis")
    parser.add_argument("--day", type=str, default=None,
                        help="YYYY-MM-DD (default: newest active)")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Filter to one run_id (default: all runs "
                             "in the newest day)")
    parser.add_argument("--list-runs", action="store_true",
                        help="List run_ids in the day, then exit")
    args = parser.parse_args()

    # Determine the day first
    if args.day:
        day = args.day
    else:
        from backtest.shadow_analysis import load_shadow_newest
        peek = load_shadow_newest()
        day = peek.get("day")

    if not day:
        print("No shadow records found.")
        return 1

    if args.list_runs:
        runs = list_runs(day)
        print(f"Day: {day}")
        for r in runs:
            print(f"  run_id: {r}")
        return 0

    payload = load_shadow_day(day, run_id=args.run_id)

    if not payload["decisions"]:
        print(f"No shadow records found (day={payload.get('day')}).")
        print("Run scripts/shadow_run.py first.")
        return 1

    trades = replay_trades(payload["decisions"])
    open_times = [int(d["candle_open_time"]) for d in payload["decisions"]]
    if len(open_times) >= 2:
        span_s = (max(open_times) - min(open_times)) / 1000.0
        period_days = max(span_s / 86400.0, 1e-9)
    else:
        period_days = None

    stats = compute_metrics(trades, 10000.0, period_days=period_days)

    print(f"\nDay: {payload['day']}")
    print(f"Decisions: {len(payload['decisions'])}")
    print(f"Replayed trades: {len(trades)}")
    print()
    print(print_comparison(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())