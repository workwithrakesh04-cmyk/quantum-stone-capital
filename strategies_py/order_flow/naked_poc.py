"""Naked POC - untested Point of Control magnet."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class NakedPOCStrategy(BaseStrategy):
    NAME = "naked_poc"
    BOOK_ID = "VP"
    CATEGORY = "volume_profile"
    TIMEFRAMES = ["5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 60:
            return self._hold_signal("not enough candles")

        session1 = candles[-60:-30]
        session2 = candles[-30:]

        buckets = {}
        bucket_size = 10.0
        for c in session1:
            mid = (c["high"] + c["low"]) / 2
            bucket = round(mid / bucket_size) * bucket_size
            buckets[bucket] = buckets.get(bucket, 0) + c["volume"]

        if not buckets:
            return self._hold_signal("no session1 buckets")

        poc = max(buckets, key=buckets.get)

        for c in session2:
            if c["low"] <= poc <= c["high"]:
                return self._hold_signal("POC retested")

        curr = candles[-1]
        curr_price = curr["close"]
        dist_pct = abs(curr_price - poc) / poc * 100
        if dist_pct > 0.3:
            return self._hold_signal(f"naked POC {dist_pct:.2f}% away")

        if curr_price > poc and self._is_bearish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.68,
                weight=self._get_rule_weight("short", "naked"),
                reason=f"Naked POC magnet at {poc:.0f} (from above)",
                confluences=["naked_poc"],
                timeframe=self.timeframe,
                price=curr_price, ts=curr.get("open_time", 0),
            )

        if curr_price < poc and self._is_bullish(curr):
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.68,
                weight=self._get_rule_weight("long", "naked"),
                reason=f"Naked POC magnet at {poc:.0f} (from below)",
                confluences=["naked_poc"],
                timeframe=self.timeframe,
                price=curr_price, ts=curr.get("open_time", 0),
            )

        return self._hold_signal("naked POC but no direction")
