"""
Volume Price Analysis (Coulling).
Detects effort/result anomalies and key VPA signals.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VPABar:
    high: float
    low: float
    close: float
    open: float
    volume: float


class VPAEngine:
    """
    Coulling's VPA: compares effort (volume) to result (price movement).
    """

    def __init__(self, avg_volume_window: int = 20):
        self.avg_volume_window = avg_volume_window

    def classify_bar(
        self,
        bar: VPABar,
        history: List[VPABar],
    ) -> Optional[str]:
        """
        Returns one of:
          - 'high_volume_wide_spread'      (strength)
          - 'high_volume_narrow_spread'    (weakness / absorption)
          - 'low_volume_wide_spread'       (false move)
          - 'low_volume_narrow_spread'     (consolidation)
        """
        if len(history) < self.avg_volume_window:
            return None

        avg_vol = sum(b.volume for b in history[-self.avg_volume_window:]) / self.avg_volume_window
        if avg_vol == 0:
            return None

        avg_spread = sum(b.high - b.low for b in history[-self.avg_volume_window:]) / self.avg_volume_window
        if avg_spread == 0:
            return None

        vol_ratio = bar.volume / avg_vol
        spread_ratio = (bar.high - bar.low) / avg_spread

        high_vol = vol_ratio >= 1.5
        low_vol = vol_ratio <= 0.7
        wide_spread = spread_ratio >= 1.3
        narrow_spread = spread_ratio <= 0.7

        if high_vol and wide_spread:
            return "high_volume_wide_spread"
        if high_vol and narrow_spread:
            return "high_volume_narrow_spread"
        if low_vol and wide_spread:
            return "low_volume_wide_spread"
        if low_vol and narrow_spread:
            return "low_volume_narrow_spread"
        return None

    def effort_vs_result(
        self,
        bar: VPABar,
        history: List[VPABar],
    ) -> str:
        """
        Effort (volume) vs Result (price change).
        Returns:
          'confirm'   — high volume, big move
          'divergence' — high volume, small move (reversal warning)
          'weak'      — low volume, big move (unsustainable)
          'quiet'     — low volume, small move (neutral)
        """
        if len(history) < self.avg_volume_window:
            return "quiet"

        avg_vol = sum(b.volume for b in history[-self.avg_volume_window:]) / self.avg_volume_window
        avg_move = sum(abs(b.close - b.open) for b in history[-self.avg_volume_window:]) / self.avg_volume_window
        if avg_vol == 0 or avg_move == 0:
            return "quiet"

        vol_ratio = bar.volume / avg_vol
        move_ratio = abs(bar.close - bar.open) / avg_move

        if vol_ratio >= 1.5 and move_ratio >= 1.3:
            return "confirm"
        if vol_ratio >= 1.5 and move_ratio <= 0.7:
            return "divergence"
        if vol_ratio <= 0.7 and move_ratio >= 1.3:
            return "weak"
        return "quiet"
