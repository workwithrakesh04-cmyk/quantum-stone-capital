"""
Harmonic Pattern Engine (Young Ho Seo).
Detects Gartley, Butterfly, Cypher, Shark, AB=CD.
Implements PCI (Pattern Completion Interval).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HarmonicPattern:
    name: str
    direction: str  # "bullish" | "bearish"
    X: float
    A: float
    B: float
    C: float
    D_ideal: float
    pci_low: float
    pci_high: float
    valid: bool
    notes: str = ""


class HarmonicEngine:
    """Ratios from Seo's Precision Harmonic Pattern Trading book."""

    TOLERANCE_DEFAULT = 0.05  # PCI +/-5%

    def _in_range(self, value: float, lo: float, hi: float, tol: float = 0.05) -> bool:
        return (lo - tol) <= value <= (hi + tol)

    def _make(self, name: str, X: float, A: float, B: float, C: float, D_ideal: float) -> HarmonicPattern:
        tol = self.TOLERANCE_DEFAULT
        return HarmonicPattern(
            name=name,
            direction="bullish" if A > X else "bearish",
            X=X, A=A, B=B, C=C,
            D_ideal=D_ideal,
            pci_low=D_ideal * (1 - tol),
            pci_high=D_ideal * (1 + tol),
            valid=True,
        )

    def detect_gartley(self, X, A, B, C) -> Optional[HarmonicPattern]:
        XA = abs(A - X); AB = abs(B - A); BC = abs(C - B)
        if XA == 0 or AB == 0:
            return None
        ab_xa = AB / XA
        bc_ab = BC / AB
        if not self._in_range(ab_xa, 0.55, 0.68):
            return None
        if not self._in_range(bc_ab, 0.35, 0.90):
            return None
        D = A + 0.786 * (X - A)
        return self._make("gartley", X, A, B, C, D)

    def detect_butterfly(self, X, A, B, C) -> Optional[HarmonicPattern]:
        XA = abs(A - X); AB = abs(B - A)
        if XA == 0:
            return None
        ab_xa = AB / XA
        if not self._in_range(ab_xa, 0.75, 0.82):
            return None
        D = A + 1.27 * (X - A)
        return self._make("butterfly", X, A, B, C, D)

    def detect_cypher(self, X, A, B, C) -> Optional[HarmonicPattern]:
        XA = abs(A - X); AB = abs(B - A); BC = abs(C - B)
        if XA == 0 or AB == 0:
            return None
        ab_xa = AB / XA
        bc_ab = BC / AB
        if not self._in_range(ab_xa, 0.35, 0.65):
            return None
        if not self._in_range(bc_ab, 1.10, 1.45):
            return None
        D = A + 0.786 * (X - A)
        return self._make("cypher", X, A, B, C, D)

    def detect_shark(self, X, A, B, C) -> Optional[HarmonicPattern]:
        D = C + 0.886 * (B - C)
        return self._make("shark", X, A, B, C, D)

    def detect_abcd(self, A, B, C) -> Optional[HarmonicPattern]:
        AB = abs(B - A); BC = abs(C - B)
        if AB == 0:
            return None
        bc_ab = BC / AB
        if not self._in_range(bc_ab, 0.55, 0.72):
            return None
        D = C + AB
        return self._make("ab_cd", A, A, B, C, D)

    def in_pci(self, price: float, pattern: HarmonicPattern) -> bool:
        return pattern.pci_low <= price <= pattern.pci_high

    def stop_loss(self, pattern: HarmonicPattern) -> float:
        pci_range = pattern.pci_high - pattern.pci_low
        return pattern.pci_low - pci_range
