"""Stacked Imbalance - consecutive same-direction imbalances."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class StackedImbalanceStrategy(BaseStrategy):
    NAME = "stacked_imbalance"
    BOOK_ID = "TD"
    CATEGORY = "order_flow"
    TIMEFRAMES = ["1m", "5m", "15m"]

    RATIO = 2.5
    MIN_CONSECUTIVE = 2

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 5:
            return self._hold_signal("not enough candles")

        if "buy_volume" not in candles[-1] or "sell_volume" not in candles[-1]:
            return self._hold_signal("no delta data")

        consecutive_buy = 0
        consecutive_sell = 0

        for c in reversed(candles[-5:]):
            bv = c.get("buy_volume", 0)
            sv = c.get("sell_volume", 0)
            if bv == 0 and sv == 0:
                break
            if sv > 0 and bv / sv >= self.RATIO:
                consecutive_buy += 1
                consecutive_sell = 0
            elif bv > 0 and sv / bv >= self.RATIO:
                consecutive_sell += 1
                consecutive_buy = 0
            else:
                break

        curr = candles[-1]

        if consecutive_buy >= self.MIN_CONSECUTIVE:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.75,
                weight=self._get_rule_weight("long", "stacked"),
                reason=f"Stacked buying imbalances ({consecutive_buy} bars)",
                confluences=["stacked_imbalance", "delta_positive"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        if consecutive_sell >= self.MIN_CONSECUTIVE:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.75,
                weight=self._get_rule_weight("short", "stacked"),
                reason=f"Stacked selling imbalances ({consecutive_sell} bars)",
                confluences=["stacked_imbalance", "delta_negative"],
                timeframe=self.timeframe,
                price=curr["close"], ts=curr.get("open_time", 0),
            )

        return self._hold_signal("no stacked imbalance")
