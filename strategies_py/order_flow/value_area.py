"""Value Area - VAH/VAL rejection (70% volume concentration edges)."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class ValueAreaStrategy(BaseStrategy):
    NAME = "value_area"
    BOOK_ID = "VP"
    CATEGORY = "volume_profile"
    TIMEFRAMES = ["5m", "15m", "1h"]

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 30:
            return self._hold_signal("not enough candles")

        buckets = {}
        bucket_size = 10.0
        for c in candles[-30:]:
            mid = (c["high"] + c["low"]) / 2
            bucket = round(mid / bucket_size) * bucket_size
            buckets[bucket] = buckets.get(bucket, 0) + c["volume"]

        if not buckets:
            return self._hold_signal("no buckets")

        total_vol = sum(buckets.values())
        target = total_vol * 0.70

        sorted_buckets = sorted(buckets.items(), key=lambda x: -x[1])
        cumulative = 0
        selected_prices = []
        for price, vol in sorted_buckets:
            cumulative += vol
            selected_prices.append(price)
            if cumulative >= target:
                break

        if not selected_prices:
            return self._hold_signal("could not compute VA")

        val = min(selected_prices)
        vah = max(selected_prices)

        curr = candles[-1]
        curr_price = curr["close"]

        if abs(curr_price - vah) / vah * 100 <= 0.05:
            if self._is_bearish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.65,
                    weight=self._get_rule_weight("short", "value"),
                    reason=f"Bearish rejection at VAH ({vah:.0f})",
                    confluences=["vah_rejection"],
                    timeframe=self.timeframe,
                    price=curr_price, ts=curr.get("open_time", 0),
                )

        if abs(curr_price - val) / val * 100 <= 0.05:
            if self._is_bullish(curr):
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.65,
                    weight=self._get_rule_weight("long", "value"),
                    reason=f"Bullish bounce at VAL ({val:.0f})",
                    confluences=["val_bounce"],
                    timeframe=self.timeframe,
                    price=curr_price, ts=curr.get("open_time", 0),
                )

        return self._hold_signal(f"price between VAH/VAL ({val:.0f}-{vah:.0f})")
