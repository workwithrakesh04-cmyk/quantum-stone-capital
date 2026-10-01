"""Apex Flow - volatility-adaptive envelope breakout."""
from typing import List
import numpy as np
from strategies_py.base import BaseStrategy
from beta_brain.signal import Signal


class ApexFlowStrategy(BaseStrategy):
    NAME = "apex_flow"
    BOOK_ID = "joat_apex_flow"
    CATEGORY = "adaptive_flow"
    TIMEFRAMES = ["5m", "15m", "1h"]
    FLOW_LEN = 34
    FLOW_ACCEL = 2.0
    ENV_MULT = 1.6
    ATR_LEN = 14
    MIN_QUALITY = 60

    def _atr(self, highs, lows, closes, period):
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, period + 1):
            h, l, pc = highs[-i], lows[-i], closes[-i-1]
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        return float(np.mean(trs))

    def _flow_baseline(self, closes):
        if len(closes) < self.FLOW_LEN + 2:
            return closes[-1] if len(closes) else 0.0
        er_change = abs(closes[-1] - closes[-self.FLOW_LEN])
        er_noise = float(np.sum(np.abs(np.diff(closes[-self.FLOW_LEN:]))))
        er = er_change / er_noise if er_noise > 0 else 0.0
        fast_sc = 2.0 / 3.0
        slow_sc = 2.0 / 31.0
        sc_raw = er * (fast_sc - slow_sc) + slow_sc
        smooth_const = min(sc_raw ** 2 * self.FLOW_ACCEL, 1.0)
        flow = closes[0]
        for v in closes[1:]:
            flow = flow + smooth_const * (v - flow)
        return flow

    def analyze(self, candles: List[dict]) -> Signal:
        if len(candles) < self.FLOW_LEN + 5:
            return self._hold_signal("not enough candles")

        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])

        flow_now = self._flow_baseline(closes)
        atr_now = self._atr(highs, lows, closes, self.ATR_LEN)
        env_up_now = flow_now + atr_now * self.ENV_MULT
        env_dn_now = flow_now - atr_now * self.ENV_MULT

        flow_prev = self._flow_baseline(closes[:-1])
        atr_prev = self._atr(highs[:-1], lows[:-1], closes[:-1], self.ATR_LEN)
        env_up_prev = flow_prev + atr_prev * self.ENV_MULT
        env_dn_prev = flow_prev - atr_prev * self.ENV_MULT

        curr_close, prev_close = closes[-1], closes[-2]
        curr = candles[-1]

        if prev_close <= env_up_prev and curr_close > env_up_now:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="LONG", confidence=0.68,
                weight=self._get_rule_weight("long", "flow"),
                reason="Apex Flow LONG (envelope breakout)",
                confluences=["apex_flow"],
                timeframe=self.timeframe,
                price=curr_close, ts=curr.get("open_time", 0),
            )
        if prev_close >= env_dn_prev and curr_close < env_dn_now:
            return Signal(
                strategy=self.NAME, book_id=self.BOOK_ID,
                direction="SHORT", confidence=0.68,
                weight=self._get_rule_weight("short", "flow"),
                reason="Apex Flow SHORT (envelope breakdown)",
                confluences=["apex_flow"],
                timeframe=self.timeframe,
                price=curr_close, ts=curr.get("open_time", 0),
            )
        return self._hold_signal("no envelope flip")
