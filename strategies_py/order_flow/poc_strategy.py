"""POC Strategy - first-touch POC with directional close filter."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class POCStrategy(BaseStrategy):
    NAME = "poc"
    BOOK_ID = "VP"
    CATEGORY = "volume_profile"
    TIMEFRAMES = ["1m", "5m", "15m", "1h"]

    BAND_PCT = 0.05
    MIN_TOUCHES_GAP = 5

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 30:
            return self._hold_signal("not enough candles")

        price_buckets = {}
        bucket_size = 10.0
        for c in candles[-30:]:
            mid = (c["high"] + c["low"]) / 2
            bucket = round(mid / bucket_size) * bucket_size
            price_buckets[bucket] = price_buckets.get(bucket, 0) + c["volume"]

        if not price_buckets:
            return self._hold_signal("no volume buckets")

        poc = max(price_buckets, key=price_buckets.get)
        if poc <= 0:
            return self._hold_signal("invalid POC")
        curr = candles[-1]
        curr_price = curr["close"]

        dist_pct = abs(curr_price - poc) / poc * 100
        if dist_pct > self.BAND_PCT:
            return self._hold_signal(f"price {dist_pct:.3f}% from POC")

        for c in candles[-self.MIN_TOUCHES_GAP:-1]:
            mid = (c["high"] + c["low"]) / 2
            if abs(mid - poc) / poc * 100 <= self.BAND_PCT:
                return self._hold_signal("recent POC touch (wait)")

        c_range = curr["high"] - curr["low"]
        if c_range <= 0:
            return self._hold_signal("zero range candle")

        close_pos = (curr["close"] - curr["low"]) / c_range

        if close_pos > 0.65:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.62,
                weight=self._get_rule_weight("long", "POC"),
                reason=f"Price at POC ({poc:.0f}) bullish close",
                confluences=["poc_touch"],
                timeframe=self.timeframe,
                price=curr_price, ts=curr.get("open_time", 0),
            )

        if close_pos < 0.35:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.62,
                weight=self._get_rule_weight("short", "POC"),
                reason=f"Price at POC ({poc:.0f}) bearish close",
                confluences=["poc_touch"],
                timeframe=self.timeframe,
                price=curr_price, ts=curr.get("open_time", 0),
            )

        return self._hold_signal("at POC but no direction")
