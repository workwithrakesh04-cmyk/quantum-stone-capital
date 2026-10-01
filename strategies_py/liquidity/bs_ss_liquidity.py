"""Buyside & Sellside Liquidity - clustered pivots, ATR band."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class BuysideSellsideLiquidityStrategy(BaseStrategy):
    NAME = "bs_ss_liquidity"
    BOOK_ID = "luxalgo_bs_ss"
    CATEGORY = "liquidity"
    TIMEFRAMES = ["5m", "15m", "1h"]

    PIVOT_LEN = 7
    LIQ_MARGIN = 10 / 6.9
    MIN_CLUSTER_COUNT = 3
    ATR_LEN = 10

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h = highs[-i]; l = lows[-i]; pc = closes[-i - 1]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return float(np.mean(trs))

    def _find_pivot_highs(self, highs, lookback, count=20):
        pivots = []
        for i in range(len(highs) - lookback - 1, max(lookback, len(highs) - 60), -1):
            if i < lookback or i >= len(highs):
                continue
            is_pivot = True
            for j in range(1, lookback + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_pivot = False
                    break
            if is_pivot:
                pivots.append((i, highs[i]))
                if len(pivots) >= count:
                    break
        return pivots

    def _find_pivot_lows(self, lows, lookback, count=20):
        pivots = []
        for i in range(len(lows) - lookback - 1, max(lookback, len(lows) - 60), -1):
            if i < lookback or i >= len(lows):
                continue
            is_pivot = True
            for j in range(1, lookback + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_pivot = False
                    break
            if is_pivot:
                pivots.append((i, lows[i]))
                if len(pivots) >= count:
                    break
        return pivots

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 50:
            return self._hold_signal("not enough candles")

        highs = np.array([c["high"] for c in candles], dtype=np.float64)
        lows = np.array([c["low"] for c in candles], dtype=np.float64)
        closes = np.array([c["close"] for c in candles], dtype=np.float64)

        atr = self._atr(highs, lows, closes, self.ATR_LEN)
        if atr <= 0:
            return self._hold_signal("ATR is zero")

        band = atr / self.LIQ_MARGIN
        curr = candles[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]

        pivot_highs = self._find_pivot_highs(highs, self.PIVOT_LEN)
        pivot_lows = self._find_pivot_lows(lows, self.PIVOT_LEN)

        cluster_high_price = None
        cluster_high_count = 0
        if pivot_highs:
            ref_price = pivot_highs[0][1]
            cluster = [p for p in pivot_highs if abs(p[1] - ref_price) < band]
            cluster_high_count = len(cluster)
            if cluster_high_count >= self.MIN_CLUSTER_COUNT:
                cluster_high_price = float(np.mean([p[1] for p in cluster]))

        cluster_low_price = None
        cluster_low_count = 0
        if pivot_lows:
            ref_price = pivot_lows[0][1]
            cluster = [p for p in pivot_lows if abs(p[1] - ref_price) < band]
            cluster_low_count = len(cluster)
            if cluster_low_count >= self.MIN_CLUSTER_COUNT:
                cluster_low_price = float(np.mean([p[1] for p in cluster]))

        if cluster_low_price is not None:
            if curr_low < cluster_low_price and curr_close > cluster_low_price:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="LONG", confidence=0.72,
                    weight=self._get_rule_weight("long", "liquidity"),
                    reason=f"Sellside sweep below {cluster_low_price:.0f} (cluster of {cluster_low_count})",
                    confluences=["liquidity_sweep", "sellside"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        if cluster_high_price is not None:
            if curr_high > cluster_high_price and curr_close < cluster_high_price:
                return Signal(
                    strategy=self.NAME, book_id=self.BOOK_ID,
                    direction="SHORT", confidence=0.72,
                    weight=self._get_rule_weight("short", "liquidity"),
                    reason=f"Buyside sweep above {cluster_high_price:.0f} (cluster of {cluster_high_count})",
                    confluences=["liquidity_sweep", "buyside"],
                    timeframe=self.timeframe,
                    price=curr_close, ts=curr.get("open_time", 0),
                )

        return self._hold_signal(f"no sweep (buy={cluster_high_count} sell={cluster_low_count})")
