"""
Daily brain trainer (stub - Delivery 1).

Full implementation lands in Delivery 3.

Usage:
    python scripts/train_brain_daily.py
    python scripts/train_brain_daily.py --date 2026-10-01
    python scripts/train_brain_daily.py --rollback 2026-09-28
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Daily brain trainer (stub)")
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--rollback", type=str, default=None)
    args = parser.parse_args()

    if args.rollback:
        logger.warning("rollback not yet implemented (Delivery 3)")
        return 1

    logger.info("train_brain_daily: stub called")
    logger.info(f"  date_arg={args.date}")
    logger.info("  Full logic arrives in Delivery 3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
