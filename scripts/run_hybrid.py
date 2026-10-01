"""Hybrid runner: QSC Brain + Beta Brain + Arbiter. Dry run only.

Run as:
    python scripts/run_hybrid.py --once
    python -m scripts.run_hybrid --once
"""
import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.state import get_state, Decision
from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2
from beta_brain.beta_brain import BetaBrain
from consensus.arbiter import ConsensusArbiter
from consensus.audit import ConsensusAudit
from utils.logger import logger


SYMBOLS = ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "XAUUSD", "SPY", "SOLUSD"]


def wait_for_feeds(state, symbols, max_wait_seconds=30.0, min_symbols=3):
    started = time.time()
    while (time.time() - started) < max_wait_seconds:
        ready = [s for s in symbols if state.feeds.latest_price(s) is not None]
        if len(ready) >= min_symbols:
            logger.info("Feeds ready: " + str(len(ready)) + "/" + str(len(symbols)))
            return len(ready)
        time.sleep(1.0)
    ready = [s for s in symbols if state.feeds.latest_price(s) is not None]
    logger.warning("Feed warmup timeout: " + str(len(ready)) + "/" + str(len(symbols)))
    return len(ready)


def build_context(state, symbol, timeframe="5m"):
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
        symbol=symbol, timeframe=timeframe,
        closes=closes, highs=highs, lows=lows, opens=closes,
        volumes=[0.0] * len(closes),
        momentum=momentum, rsi=50.0, delta=0.0, volatility=0.01, bos=None,
        regime="trending_up" if (momentum or 0) > 0 else "trending_down",
        session="london", active_killzones=["london_kz"],
        passes_filter=False, agreeing_frameworks=["gud-price", "binance"],
    )


def run_once(qsc_brain, beta_brain, arbiter, audit, state):
    count = 0
    for symbol in SYMBOLS:
        try:
            ctx = build_context(state, symbol)
        except ValueError as e:
            logger.warning("hybrid: " + symbol + " skipped: " + str(e))
            continue
        try:
            qsc_result = qsc_brain.run(ctx, account_name="personal")
            beta_verdict = beta_brain.run(ctx, account_type="personal") if beta_brain else None
            decision = arbiter.decide(qsc_result, beta_verdict)

            record = {
                "symbol": symbol, "timeframe": ctx.timeframe,
                "qsc": {"decision": qsc_result.decision,
                        "direction": qsc_result.direction,
                        "confidence": qsc_result.confidence,
                        "strategy_name": qsc_result.strategy_name,
                        "reasons": qsc_result.reasons[:5]},
                "beta": {"final_decision": getattr(beta_verdict, "final_decision", None) if beta_verdict else None,
                         "direction": decision.beta_direction,
                         "confidence": decision.beta_confidence,
                         "winner": getattr(beta_verdict, "debate_winner", None) if beta_verdict else None},
                "arbiter": decision.to_dict(),
            }
            audit.write(record)

            routing = qsc_result.metadata.get("routing", {}) if hasattr(qsc_result, "metadata") else {}
            d = Decision(
                symbol=symbol, direction=qsc_result.direction,
                confidence=qsc_result.confidence, decision=qsc_result.decision,
                strategy_name=qsc_result.strategy_name,
                reasons=qsc_result.reasons[:5],
                account_name=routing.get("account_name"),
                routing_reason=routing.get("reason"),
                rule_source=routing.get("rule_source"),
                alpha_direction=qsc_result.direction,
                alpha_confidence=qsc_result.confidence,
                beta_direction=decision.beta_direction,
                beta_confidence=decision.beta_confidence,
                consensus=decision.consensus,
                size_multiplier=decision.size_multiplier,
            )
            state.add_decision(d)
            count += 1
            logger.info("hybrid: " + symbol + " qsc=" + str(qsc_result.direction)
                        + " beta=" + str(decision.beta_direction)
                        + " consensus=" + str(decision.consensus)
                        + " final=" + str(decision.direction)
                        + " size=" + str(decision.size_multiplier) + "x")
        except Exception as e:
            logger.error("hybrid: " + symbol + " failed: " + str(e))
    return count


def main():
    parser = argparse.ArgumentParser(description="QSC Hybrid Loop (dry run)")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--warmup", type=float, default=30.0)
    parser.add_argument("--min-symbols", type=int, default=3)
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  Hybrid Brain Loop (dry run, no execution)")
    logger.info("=" * 60)

    state = get_state()
    try:
        state.feeds.start_all()
    except Exception:
        pass
    wait_for_feeds(state, SYMBOLS, max_wait_seconds=args.warmup, min_symbols=args.min_symbols)

    qsc_brain = MainBrainV2(broker_pool=state.pool)
    try:
        beta_brain = BetaBrain()
    except Exception as e:
        logger.error("BetaBrain init failed: " + str(e))
        beta_brain = None
    arbiter = ConsensusArbiter()
    audit = ConsensusAudit()

    if args.once:
        n = run_once(qsc_brain, beta_brain, arbiter, audit, state)
        logger.info("One-shot complete: " + str(n) + " decisions")
        return

    logger.info("Loop starting (interval=" + str(args.interval) + "s)")
    try:
        while True:
            n = run_once(qsc_brain, beta_brain, arbiter, audit, state)
            logger.info("Pass complete: " + str(n) + " decisions")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Loop stopped")


if __name__ == "__main__":
    main()
