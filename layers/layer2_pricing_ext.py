"""Layer 2 extension - Elliott Wave + Harmonic + Fibonacci targets."""
from core.pricing_engine import PricingEngine
from core.elliott_wave import ElliottWaveEngine, WavePoint
from core.harmonic import HarmonicEngine
from utils.fibonacci import retracement_levels, extension_levels


class Layer2PricingExt:
    def __init__(self):
        self.pricing = PricingEngine()
        self.ew = ElliottWaveEngine()
        self.harmonic = HarmonicEngine()

    # --- Fibonacci wrappers ---
    def retracements(self, start: float, end: float) -> dict:
        return retracement_levels(start, end)

    def extensions(self, start: float, end: float) -> dict:
        return extension_levels(start, end)

    # --- Elliott Wave ---
    def validate_impulse(self, waves: dict) -> dict:
        return self.ew.validate_impulse(waves)

    def wave3_targets(self, w1_start: float, w1_end: float, w2_end: float) -> dict:
        return self.ew.wave3_targets(w1_start, w1_end, w2_end)

    def wave5_targets(self, w4_end: float, w3_len: float) -> dict:
        return self.ew.wave5_targets(w4_end, w3_len)

    # --- Harmonic ---
    def detect_pattern(self, name: str, *args) -> object:
        fn = getattr(self.harmonic, "detect_" + name, None)
        if fn is None:
            return None
        return fn(*args)

    def in_pci(self, price: float, pattern) -> bool:
        return self.harmonic.in_pci(price, pattern)

    def harmonic_stop(self, pattern) -> float:
        return self.harmonic.stop_loss(pattern)
