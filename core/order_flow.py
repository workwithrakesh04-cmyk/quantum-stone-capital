"""
Order flow analysis: delta, cumulative delta, absorption, imbalance.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OrderFlowBar:
    """Aggregated order flow for a single bar."""
    bid_volume: float
    ask_volume: float
    delta: float
    cumulative_delta: float
    high: float
    low: float
    close: float


class OrderFlowEngine:
    """
    Computes delta, cumulative delta, and imbalance from bid/ask volumes.
    Delta = ask - bid (aggressive buyers minus aggressive sellers).
    """

    def __init__(self):
        self._cumulative_delta = 0.0

    def compute_delta(self, bid_volume: float, ask_volume: float) -> float:
        return ask_volume - bid_volume

    def compute_bar(
        self,
        bid_volume: float,
        ask_volume: float,
        high: float,
        low: float,
        close: float,
    ) -> OrderFlowBar:
        delta = self.compute_delta(bid_volume, ask_volume)
        self._cumulative_delta += delta
        return OrderFlowBar(
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            delta=delta,
            cumulative_delta=self._cumulative_delta,
            high=high,
            low=low,
            close=close,
        )

    def reset(self) -> None:
        self._cumulative_delta = 0.0

    @property
    def cumulative_delta(self) -> float:
        return self._cumulative_delta

    # ---------- detection methods ----------

    def detect_absorption(
        self,
        bars: List[OrderFlowBar],
        lookback: int = 5,
    ) -> Optional[str]:
        """
        Absorption: large delta but no price progress = big player absorbing.
        Returns 'bullish_absorb' | 'bearish_absorb' | None
        """
        if len(bars) < lookback:
            return None
        recent = bars[-lookback:]
        total_delta = sum(b.delta for b in recent)
        price_range = max(b.high for b in recent) - min(b.low for b in recent)
        # Normalize delta by price range
        if price_range <= 0:
            return None
        delta_intensity = abs(total_delta) / price_range
        # Very high delta but very small range = absorption
        if delta_intensity > 10 and price_range < 1.0:
            if total_delta > 0:
                return "bullish_absorb"
            return "bearish_absorb"
        return None

    def detect_imbalance(
        self,
        bar: OrderFlowBar,
        threshold: float = 3.0,
    ) -> Optional[str]:
        """
        Bid/ask imbalance: strong one-sided flow.
        Returns 'buy_imbalance' | 'sell_imbalance' | None
        """
        if bar.bid_volume <= 0 or bar.ask_volume <= 0:
            return None
        ratio = bar.ask_volume / bar.bid_volume
        if ratio >= threshold:
            return "buy_imbalance"
        if ratio <= 1.0 / threshold:
            return "sell_imbalance"
        return None

    def classify_flow(self, delta: float) -> str:
        if delta > 0:
            return "bullish"
        if delta < 0:
            return "bearish"
        return "neutral"
