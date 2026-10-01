"""Adaptive RSI ML - RSI structure + k-NN analog."""
from typing import List
from collections import deque
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class AdaptiveRSIMLStrategy(BaseStrategy):
    NAME = "adaptive_rsi_ml"
    BOOK_ID = "zeiierman_adaptive_rsi_ml"
    CATEGORY = "ml_rsi_structural"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MEMORY_DEPTH = 300
    K_NEIGHBORS = 9
    HORIZON_BARS = 4
    SPACING_BARS = 4
    RSI_PERIOD = 14
    MIN_DRIVE = 0.45
    MIN_ANALOG = 0.40
    MIN_BANK = 40
    COOLDOWN_BARS = 5
    WARMUP_BARS = 150

    def __init__(self, timeframe: str = "5m"):
        super().__init__(timeframe)
        self._bank = deque(maxlen=self.MEMORY_DEPTH)
        self._bar_count = 0
        self._last_fire_bar = -999
        self._last_dir = 0

    def _rsi_series(self, closes, period):
        n = len(closes)
        rsi = np.full(n, 50.0)
        if n < period + 1:
            return rsi
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        for i in range(period, n):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
            rsi[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        return rsi

    def _knn_vote(self, fvec):
        if len(self._bank) < self.MIN_BANK:
            return 0.0, 0.0, 0
        candidates = []
        bank = list(self._bank)
        for i in range(0, len(bank), self.SPACING_BARS):
            rvec, outcome = bank[i]
            gap = float(np.sum(np.log1p(np.abs(fvec - rvec))))
            candidates.append((gap, outcome))
        candidates.sort(key=lambda x: x[0])
        top_k = candidates[:self.K_NEIGHBORS]
        total = 0.0; score = 0.0
        for gap, cls in top_k:
            w = 1.0 / (1.0 + gap)
            total += w; score += cls * w
        if total == 0:
            return 0.0, 0.0, 0
        analog = score / total
        return analog, abs(analog) / 3.0, len(top_k)

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < 60:
            return self._hold_signal("not enough candles")
        self._bar_count += 1

        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        closes = np.array([c["close"] for c in candles])
        rsi = self._rsi_series(closes, self.RSI_PERIOD)
        i = len(closes) - 1
        if i < self.RSI_PERIOD + 10:
            return self._hold_signal("warmup")

        rsi_norm = (rsi[i] - 50.0) / 50.0
        slope = max(-1.0, min(1.0, (rsi[i] - rsi[i - 5]) / 50.0))
        price_change = (closes[i] - closes[i - 10]) / (closes[i - 10] + 1e-9)
        rsi_change = (rsi[i] - rsi[i - 10]) / 50.0
        divergence = max(-1.0, min(1.0, (rsi_change - price_change) * 3.0))
        recent_rsi = rsi[i - 20:i + 1]
        rsi_std = float(np.std(recent_rsi)) / 50.0
        regime = max(-1.0, min(1.0, (rsi_std - 0.15) * 5.0))
        recent50 = rsi[max(0, i - 50):i + 1]
        pct_feat = (float(np.mean(recent50 <= rsi[i])) - 0.5) * 2.0 if len(recent50) > 5 else 0.0
        accel = max(-1.0, min(1.0, (rsi[i] - 2*rsi[i-1] + rsi[i-2]) / 50.0 * 5.0)) if i >= 3 else 0.0
        fvec = np.array([rsi_norm, slope, divergence, regime, pct_feat, accel])

        if len(closes) > self.HORIZON_BARS + 20:
            past = len(closes) - 1 - self.HORIZON_BARS
            past_fvec = fvec  # placeholder for simplicity
            move = closes[-1] - closes[past]
            trs = []
            for j in range(1, 15):
                if len(closes) > j:
                    h, l, pc = highs[-j], lows[-j], closes[-j-1]
                    trs.append(max(h-l, abs(h-pc), abs(l-pc)))
            atr = float(np.mean(trs)) if trs else 0.0
            band = 0.5 * atr if atr > 0 else 0.0
            if band > 0:
                outcome = 0
                if move > 2*band: outcome = 3
                elif move > band: outcome = 2
                elif move > 0: outcome = 1
                elif move < -2*band: outcome = -3
                elif move < -band: outcome = -2
                elif move < 0: outcome = -1
                self._bank.append((past_fvec, outcome))

        if self._bar_count < self.WARMUP_BARS:
            return self._hold_signal("warmup")
        if self._bar_count - self._last_fire_bar < self.COOLDOWN_BARS:
            return self._hold_signal("cooldown")

        analog, agreement, k_used = self._knn_vote(fvec)
        if k_used < self.K_NEIGHBORS // 2:
            return self._hold_signal("not enough neighbors")
        drive = min(1.0, abs(analog)/2.0*0.6 + agreement*0.4)
        if drive < self.MIN_DRIVE or abs(analog) < self.MIN_ANALOG:
            return self._hold_signal(f"drive={drive:.2f} analog={analog:.2f}")

        direction = None
        if analog > self.MIN_ANALOG and (rsi_norm < 0.2 or divergence > 0.3) and slope > -0.1:
            direction = "LONG"
        elif analog < -self.MIN_ANALOG and (rsi_norm > -0.2 or divergence < -0.3) and slope < 0.1:
            direction = "SHORT"
        if direction is None:
            return self._hold_signal("no alignment")
        if direction == ("LONG" if self._last_dir == 1 else "SHORT"):
            return self._hold_signal("same as last")

        curr = candles[-1]
        self._last_fire_bar = self._bar_count
        self._last_dir = 1 if direction == "LONG" else -1
        return Signal(
            strategy=self.NAME, book_id=self.BOOK_ID,
            direction=direction, confidence=round(min(0.72, drive*0.85), 3),
            weight=self._get_rule_weight(direction.lower(), "mean_reversion"),
            reason=f"AdaptiveRSI {direction} (analog={analog:.2f} drive={drive:.2f})",
            confluences=["adaptive_rsi", "knn_analog"],
            timeframe=self.timeframe,
            price=closes[-1], ts=curr.get("open_time", 0),
        )
