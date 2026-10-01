"""Volume Cluster - bounce/reject at aged high-volume cluster."""
from typing import List
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class VolumeClusterStrategy(BaseStrategy):
    NAME = "volume_cluster"
    BOOK_ID = "TD"
    CATEGORY = "volume_profile"
    TIMEFRAMES = ["1m", "5m", "15m"]

    BUCKET = 10.0
    MIN_MULTIPLE = 3.0
    MAX_DIST_PCT = 0.03

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 30:
            return self._hold_signal("not enough candles")

        historical = candles[-30:-5]
        buckets = {}
        for c in historical:
            mid = (c["high"] + c["low"]) / 2
            bucket = round(mid / self.BUCKET) * self.BUCKET
            buckets[bucket] = buckets.get(bucket, 0) + c["volume"]

        if len(buckets) < 3:
            return self._hold_signal("not enough buckets")

        avg_bucket_vol = sum(buckets.values()) / len(buckets)
        clusters = {p: v for p, v in buckets.items() if v > avg_bucket_vol * self.MIN_MULTIPLE}

        if not clusters:
            return self._hold_signal("no strong cluster")

        curr = candles[-1]
        curr_price = curr["close"]

        for cluster_price in sorted(clusters.keys(), key=lambda p: abs(p - curr_price)):
            if cluster_price <= 0:
                continue
            dist_pct = abs(curr_price - cluster_price) / cluster_price * 100
            if dist_pct <= self.MAX_DIST_PCT:
                if self._is_bullish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="LONG", confidence=0.68,
                        weight=self._get_rule_weight("long", "volume"),
                        reason=f"Bullish bounce at cluster {cluster_price:.0f}",
                        confluences=["volume_cluster"],
                        timeframe=self.timeframe,
                        price=curr_price, ts=curr.get("open_time", 0),
                    )
                if self._is_bearish(curr):
                    return Signal(
                        strategy=self.NAME, book_id=self.BOOK_ID,
                        direction="SHORT", confidence=0.68,
                        weight=self._get_rule_weight("short", "volume"),
                        reason=f"Bearish reject at cluster {cluster_price:.0f}",
                        confluences=["volume_cluster"],
                        timeframe=self.timeframe,
                        price=curr_price, ts=curr.get("open_time", 0),
                    )
            break

        return self._hold_signal("no cluster nearby")
