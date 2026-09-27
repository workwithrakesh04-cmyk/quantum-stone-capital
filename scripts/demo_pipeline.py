"""
Demo: run the MainBrainV2 end-to-end on synthetic data.
Run with: python -m scripts.demo_pipeline
"""
import numpy as np

from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2
from utils.logger import logger


def make_synthetic_context(symbol="BTCUSD", timeframe="5m", n=200, regime="trending_up"):
    np.random.seed(42)
    drift = 0.0005 if regime == "trending_up" else -0.0005
    closes = list(np.cumsum(np.random.randn(n) * 0.01 + drift) + 100)
    highs = [c + abs(np.random.randn() * 0.005) + 0.002 for c in closes]
    lows = [c - abs(np.random.randn() * 0.005) - 0.002 for c in closes]
    opens = [c - drift * 0.5 for c in closes]
    volumes = [1000 + i * 5 for i in range(n)]

    momentum = (closes[-1] - closes[-20]) / closes[-20]
    return MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        closes=closes,
        highs=highs,
        lows=lows,
        opens=opens,
        volumes=volumes,
        momentum=momentum,
        rsi=35.0,
        delta=100.0,
        volatility=0.015,
        bos="BOS_BULLISH",
        regime=regime,
        session="london",
        active_killzones=["london_kz"],
        passes_filter=True,
        agreeing_frameworks=["wyckoff", "smc"],
    )


def main():
    logger.info("Starting demo pipeline")
    brain = MainBrainV2()
    for regime in ["trending_up", "trending_down", "ranging"]:
        ctx = make_synthetic_context(regime=regime)
        result = brain.run(ctx, account_name="personal")
        logger.info(
            "regime=" + regime
            + " decision=" + result.decision
            + " direction=" + result.direction
            + " confidence=" + str(round(result.confidence, 2))
            + " strategy=" + str(result.strategy_name)
            + " reasons=" + str(result.reasons)
        )
    logger.info("Demo pipeline done")


if __name__ == "__main__":
    main()
