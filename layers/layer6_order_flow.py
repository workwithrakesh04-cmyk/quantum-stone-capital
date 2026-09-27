"""Layer 6 - Order Flow. Wraps order flow + footprint + VPA engines."""
from core.order_flow import OrderFlowEngine
from core.footprint import FootprintEngine
from core.vpa import VPAEngine


class Layer6OrderFlow:
    def __init__(self, avg_volume_window: int = 20):
        self.of = OrderFlowEngine()
        self.fp = FootprintEngine()
        self.vpa = VPAEngine(avg_volume_window=avg_volume_window)

    # --- order flow ---
    def bar(self, bid_volume, ask_volume, high, low, close):
        return self.of.compute_bar(bid_volume, ask_volume, high, low, close)

    def cumulative_delta(self) -> float:
        return self.of.cumulative_delta

    def reset(self) -> None:
        self.of.reset()

    # --- footprint ---
    def footprint_bar(self, ticks):
        return self.fp.build_bar(ticks)

    def footprint_imbalances(self, bar, ratio=3.0):
        return self.fp.find_imbalances(bar, ratio=ratio)

    def footprint_absorption(self, bar, min_volume=100.0):
        return self.fp.detect_absorption(bar, min_volume=min_volume)

    # --- VPA ---
    def classify_vpa(self, bar, history):
        return self.vpa.classify_bar(bar, history)

    def effort_vs_result(self, bar, history):
        return self.vpa.effort_vs_result(bar, history)
