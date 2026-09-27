"""
Brain loop: runs alongside the dashboard and makes decisions.

Usage:
    python -m scripts.run_brain                # run in foreground
    python -m scripts.run_brain --once         # one pass, then exit
    python -m scripts.run_brain --interval 30  # poll every 30s
    python -m scripts.run_brain --warmup 20    # wait up to 20s for feeds
"""
import argparse
import time

from dashboard.state import get_state, Decision
from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2
from utils.logger import logger


SYMBOLS = ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "XAUUSD", "SPY", "SOLUSD"]


def wait_for_feeds(state, symbols, max_wait_seconds: float = 30.0,
                   min_symbols: int = 3) -> int:
    """
    Wait until at least `min_symbols` symbols have a price.
    Returns the number of symbols that got a price.
    """
    started = time.time()
    while (time.time() - started) < max_wait_seconds:
        ready = [s for s in symbols if state.feeds.latest_price(s) is not None]
        if len(ready) >= min_symbols:
            logger.info(
                "Feeds ready: " + str(len(ready)) + "/" + str(len(symbols))
                + " symbols (" + ", ".join(ready) + ")"
            )
            return len(ready)
        logger.info(
            "Waiting for feeds... " + str(len(ready)) + "/" + str(len(symbols))
            + " ready (" + str(round(time.time() - started, 1)) + "s)"
        )
        time.sleep(1.0)

    ready = [s for s in symbols if state.feeds.latest_price(s) is not None]
    logger.warning(
        "Feed warmup timeout: only " + str(len(ready)) + "/" + str(len(symbols))
        + " symbols ready"
    )
    return len(ready)


def build_context(state, symbol: str, timeframe: str = "5m") -> MarketContext:
    """Build a MarketContext from live feed prices."""
    price = state.feeds.latest_price(symbol)
    if price is None:
        raise ValueError("no price for " + symbol)

    key = "_hist_" + symbol
    hist = getattr(state, key, None)
    if hist is None:
        hist = []
        setattr(state, key, hist)
    hist.append(price)
    if len(hist) > 200:
        del hist[:-200]

    closes = list(hist)
    highs = [c * 1.0005 for c in closes]
    lows = [c * 0.9995 for c in closes]

    momentum = None
    if len(closes) >= 20:
        momentum = (closes[-1] - closes[-20]) / closes[-20]

    return MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        closes=closes,
        highs=highs,
        lows=lows,
        opens=closes,
        volumes=[0.0] * len(closes),
        momentum=momentum,
        rsi=50.0,
        delta=0.0,
        volatility=0.01,
        bos=None,
        regime="trending_up" if (momentum or 0) > 0 else "trending_down",
        session="london",
        active_killzones=["london_kz"],
        passes_filter=False,
        agreeing_frameworks=["gud-price", "binance"],
    )


def run_once(brain: MainBrainV2, state) -> int:
    """Run one decision pass across all symbols. Skips symbols without prices."""
    count = 0
    for symbol in SYMBOLS:
        try:
            ctx = build_context(state, symbol)
        except ValueError as e:
            logger.warning("brain: " + symbol + " skipped: " + str(e))
            continue
        try:
            result = brain.run(ctx, account_name="personal")
            decision = Decision(
                symbol=symbol,
                direction=result.direction,
                confidence=result.confidence,
                decision=result.decision,
                strategy_name=result.strategy_name,
                reasons=result.reasons[:5],
            )
            state.add_decision(decision)
            count += 1
            logger.info(
                "brain: " + symbol + " -> " + result.decision + " "
                + result.direction + " conf=" + str(round(result.confidence, 2))
                + " strategy=" + str(result.strategy_name)
            )
        except Exception as e:
            logger.error("brain: " + symbol + " failed: " + str(e))
    return count


def main():
    parser = argparse.ArgumentParser(description="Quantum Stone Capital - Brain Loop")
    parser.add_argument("--once", action="store_true", help="One pass, then exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between passes")
    parser.add_argument("--warmup", type=float, default=30.0, help="Max seconds to wait for feeds")
    parser.add_argument("--min-symbols", type=int, default=3, help="Min symbols required before starting")
    args = parser.parse_args()

    state = get_state()

    # Ensure feeds are running
    try:
        state.feeds.start_all()
    except Exception:
        pass

    # Wait for feeds to warm up
    logger.info("Brain loop: waiting for feeds to warm up (max " + str(args.warmup) + "s)")
    wait_for_feeds(state, SYMBOLS, max_wait_seconds=args.warmup, min_symbols=args.min_symbols)

    logger.info("Brain loop starting (interval=" + str(args.interval) + "s)")
    brain = MainBrainV2()

    if args.once:
        n = run_once(brain, state)
        logger.info("One-shot pass complete: " + str(n) + " decisions")
        return

    try:
        while True:
            n = run_once(brain, state)
            logger.info("Pass complete: " + str(n) + " decisions")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Brain loop stopped")


if __name__ == "__main__":
    main()
