"""RMD Trail - Root Mean Square Deviation trail flip."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class RMDTrailStrategy(BaseStrategy):
    NAME = "rmd_trail"
    BOOK_ID = "lyrors_rmd"
    CATEGORY = "adaptive_trend"
    TIMEFRAMES = ["5m", "15m", "1h"]
    MA_LEN = 21
    RMSD_LEN = 20
    MIN_DEV = 0.5

    def _ema(self, values, period):
        if len(values) < period:
            return float(np.mean(values)) if len(values) > 0 else 0.0
        k = 2.0 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return float(ema)

    def _rmsd(self, values, ma, period):
        if len(values) < period:
            return 0.0
        return float(np.sqrt(np.mean((values[-period:] - ma) ** 2)))

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < max(self.MA_LEN, self.RMSD_LEN) + 10:
            return self._hold_signal("not enough candles")
        closes = np.array([c["close"] for c in candles])

        ma_now = self._ema(closes, self.MA_LEN)
        rmsd_now = self._rmsd(closes, ma_now, self.RMSD_LEN)
        dev_now = (closes[-1] - ma_now) / rmsd_now if rmsd_now > 0 else 0.0

        ma_prev = self._ema(closes[:-1], self.MA_LEN)
        rmsd_prev = self._rmsd(closes[:-1], ma_prev, self.RMSD_LEN)
        dev_prev = (closes[-2] - ma_prev) / rmsd_prev if rmsd_prev > 0 else 0.0

        trend_now = 1 if dev_now > 0 else -1
        trend_prev = 1 if dev_prev > 0 else -1

        if abs(dev_now) < self.MIN_DEV:
            return self._hold_signal(f"dev too small ({dev_now:+.3f})")
        if trend_now == trend_prev:
            return self._hold_signal(f"trend={trend_now}")

        curr = candles[-1]
        conf = 0.60 + min(abs(dev_now) / 3.0, 1.0) * 0.15

        if trend_now == 1:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=round(conf, 3),
                weight=self._get_rule_weight("long", "trend"),
                reason=f"RMD Trail LONG (dev={dev_now:+.3f})",
                confluences=["rmd_flip"],
                timeframe=self.timeframe,
                price=closes[-1], ts=curr.get("open_time", 0),
            )
        return Signal(
            strategy=self.NAME, book_id=self.BOOK_ID,
            direction="SHORT", confidence=round(conf, 3),
            weight=self._get_rule_weight("short", "trend"),
            reason=f"RMD Trail SHORT (dev={dev_now:+.3f})",
            confluences=["rmd_flip"],
            timeframe=self.timeframe,
            price=closes[-1], ts=curr.get("open_time", 0),
        )
