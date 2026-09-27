"""
Base worker: each worker examines a market context and returns an argument.
Workers don't vote; they produce evidence. The Debate Engine weighs them.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Argument:
    """A single worker's argument for a trade direction."""
    worker: str          # "bull" | "bear" | "hold"
    direction: str       # "long" | "short" | "flat"
    confidence: float    # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    rationale: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.direction in ("long", "short", "flat") and 0.0 <= self.confidence <= 1.0


class BaseWorker(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, context: dict) -> Argument:
        """Examine the market context and produce an Argument."""

    def __repr__(self) -> str:
        return "<Worker " + self.name + ">"
