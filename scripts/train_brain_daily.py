"""
Daily brain trainer.

Usage:
    python scripts/train_brain_daily.py                    # train on today
    python scripts/train_brain_daily.py --date 2026-10-01  # train on specific day
    python scripts/train_brain_daily.py --rollback 2026-09-28
    python scripts/train_brain_daily.py --list             # list available state folders
    python scripts/train_brain_daily.py --status           # show current + available
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import logger
from training.trainer import Trainer
from training.rollback import Rollback


def main():
    parser = argparse.ArgumentParser(description="Daily brain trainer")
    parser.add_argument("--date", type=str, default=None,
                        help="YYYY-MM-DD to train on (default: today UTC)")
    parser.add_argument("--rollback", type=str, default=None,
                        help="YYYY-MM-DD to roll back to")
    parser.add_argument("--list", action="store_true",
                        help="list available state folders")
    parser.add_argument("--status", action="store_true",
                        help="show current pointer + available")
    args = parser.parse_args()

    rb = Rollback()

    if args.list:
        for d in rb.list_available():
            print(d)
        return 0

    if args.status:
        print(json.dumps(rb.report(), indent=2))
        return 0

    if args.rollback:
        ok = rb.rollback(args.rollback)
        print("Rollback OK" if ok else "Rollback FAILED")
        return 0 if ok else 1

    report = Trainer().train(day=args.date)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
