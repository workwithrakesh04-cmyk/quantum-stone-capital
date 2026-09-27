"""
Live trading entry point (MT5).
Run with: python -m scripts.run_live

⚠️ SAFETY:
  - Defaults to DRY RUN (no real orders placed).
  - Pass --live to actually place orders (requires env vars set).
  - Requires MT5 terminal open + MetaTrader5 Python package installed.

Environment variables:
  MT5_LOGIN     - broker account number (int)
  MT5_PASSWORD  - account password
  MT5_SERVER    - broker server name
  MT5_PATH      - (optional) path to terminal64.exe
"""
import argparse
import os
import sys

from brokers.mt5_broker import MT5Broker
from core.live_runner import LiveRunner, RunnerConfig
from core.market_context import MarketContext
from utils.logger import logger


def build_runner(live: bool, symbols: list) -> LiveRunner:
    login = os.environ.get("MT5_LOGIN")
    password = os.environ.get("MT5_PASSWORD")
    server = os.environ.get("MT5_SERVER")
    path = os.environ.get("MT5_PATH")

    broker = MT5Broker(
        login=int(login) if login else None,
        password=password,
        server=server,
        path=path,
    )

    if not broker.connect():
        logger.error("MT5 connection failed. Aborting.")
        sys.exit(1)

    config = RunnerConfig(
        symbols=symbols,
        timeframe="5m",
        poll_seconds=5.0,
        account_name="personal",
        dry_run=not live,
    )

    def context_builder(b, symbol, timeframe):
        price = b.last_price(symbol)
        return MarketContext(
            symbol=symbol,
            timeframe=timeframe,
            closes=[price] if price else [],
            highs=[price] if price else [],
            lows=[price] if price else [],
            opens=[price] if price else [],
            volumes=[0.0],
        )

    return LiveRunner(broker, config=config, context_builder=context_builder)


def main():
    parser = argparse.ArgumentParser(description="Quantum Stone Capital - Live Runner")
    parser.add_argument("--live", action="store_true",
                        help="Actually place orders (default: dry run)")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "BTCUSD", "XAUUSD"],
                        help="Symbols to trade")
    parser.add_argument("--iterations", type=int, default=1,
                        help="Number of poll iterations before stopping")
    args = parser.parse_args()

    if args.live:
        logger.warning("LIVE MODE ENABLED — real orders will be placed")
    else:
        logger.info("DRY RUN — no orders will be placed")

    runner = build_runner(live=args.live, symbols=args.symbols)
    try:
        runner.run_forever(max_iterations=args.iterations)
    finally:
        runner.broker.disconnect()
        logger.info("Live runner stopped")


if __name__ == "__main__":
    main()
