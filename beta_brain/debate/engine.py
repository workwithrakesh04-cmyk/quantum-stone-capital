"""Debate Engine - runs 3-round debate between BUY/SELL/HOLD bots.

Self-contained Beta version. No dependency on QSC's debate engine.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any

from loguru import logger

from beta_brain.signal import Signal
from beta_brain.debate.buy_bot import BuyBot
from beta_brain.debate.sell_bot import SellBot
from beta_brain.debate.hold_bot import HoldBot
from beta_brain.debate.argument_scorer import ArgumentScorer
from beta_brain.debate.transcript import Argument, DebateTranscript


class DebateEngine:
    def __init__(self):
        self.buy = BuyBot()
        self.sell = SellBot()
        self.hold = HoldBot()
        self.scorer = ArgumentScorer()

    def _market_context(self, candles: List[dict]) -> Dict[str, Any]:
        if not candles or len(candles) < 5:
            return {"momentum": 0.0, "volatility": 0.5}

        closes = [c["close"] for c in candles[-5:]]
        momentum = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0.0
        momentum = max(-1.0, min(1.0, momentum * 100))

        ranges = [c["high"] - c["low"] for c in candles[-10:]]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        price = closes[-1] if closes else 1
        volatility = avg_range / price if price > 0 else 0.5
        volatility = max(0.0, min(volatility * 10, 1.0))

        return {"momentum": momentum, "volatility": volatility}

    def run(
        self,
        signals: List[Signal],
        candles: List[dict],
        symbol: str = "BTCUSD",
        timeframe: str = "5m",
    ) -> DebateTranscript:
        logger.info(f"BetaDebate: starting 3-round debate | signals={len(signals)}")
        context = self._market_context(candles)

        r1_buy = self.buy.argue(signals, context)
        r1_sell = self.sell.argue(signals, context)
        r1_hold = self.hold.argue(signals, context)
        round1 = [r1_buy, r1_sell, r1_hold]

        r2_buy = self.buy.rebut(r1_buy, r1_sell)
        r2_sell = self.sell.rebut(r1_sell, r1_buy)
        r2_hold = self.hold.rebut(
            r1_hold,
            r1_buy if r1_buy.confidence > r1_sell.confidence else r1_sell,
        )
        round2 = [r2_buy, r2_sell, r2_hold]

        r3_buy = self.buy.close(r2_buy, context)
        r3_sell = self.sell.close(r2_sell, context)
        r3_hold = self.hold.close(r2_hold, context)
        round3 = [r3_buy, r3_sell, r3_hold]

        final_scores = {
            "BUY": r3_buy.confidence,
            "SELL": r3_sell.confidence,
            "HOLD": r3_hold.confidence,
        }

        winner = max(final_scores, key=final_scores.get)
        winner_conf = final_scores[winner]

        # HOLD override: if combined BUY+SELL conviction is weak vs HOLD
        buy_sell = final_scores["BUY"] + final_scores["SELL"]
        if buy_sell < final_scores["HOLD"] * 1.5:
            winner = "HOLD"
            winner_conf = final_scores["HOLD"]

        logger.info(f"BetaDebate: verdict {winner} @ {winner_conf:.2f}")

        return DebateTranscript(
            ts=int(datetime.now(timezone.utc).timestamp() * 1000),
            symbol=symbol,
            timeframe=timeframe,
            signals_input=[s.to_dict() for s in signals],
            rounds=[round1, round2, round3],
            winner=winner,
            winner_confidence=winner_conf,
            final_scores=final_scores,
        )
