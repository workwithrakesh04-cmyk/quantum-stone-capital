"""
Paper-trading entry point.
Run with: python -m scripts.run_paper
"""
from brokers.paper_broker import PaperBroker
from core.live_runner import LiveRunner, RunnerConfig
from core.market_context import MarketContext
from utils.logger import logger
import numpy as np


def make_context(broker, symbol, timeframe):
    """Build a slightly richer context using synthetic history for demo."""
    np.random.seed(42)
    n = 120
    closes = list(np.cumsum(np.random.randn(n) * 0.01) + (broker.last_price(symbol) or 100))
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    momentum = (closes[-1] - closes[-20]) / closes[-20]
    return MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        closes=closes, highs=highs, lows=lows, opens=closes, volumes=[1000] * n,
        momentum=momentum, rsi=40.0, delta=50.0,
        regime="trending_up", session="london",
        active_killzones=["london_kz"], passes_filter=True,
        agreeing_frameworks=["wyckoff", "smc"],
    )


def main():
    logger.info("Starting paper trading run")
    broker = PaperBroker(starting_balance=10000.0, prices={"BTCUSD": 40000.0})
    broker.connect()

    config = RunnerConfig(
        symbols=["BTCUSD"],
        timeframe="5m",
        poll_seconds=1.0,
        account_name="personal",
        dry_run=True,   # never place real orders in paper mode
    )

    runner = LiveRunner(broker, config=config, context_builder=make_context)
    results = runner.tick_once()
    for r in results:
        logger.info("paper_result: " + str(r))

    broker.disconnect()
    logger.info("Paper trading run done")


if __name__ == "__main__":
    main()
