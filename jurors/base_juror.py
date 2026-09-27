"""
Base juror: each juror validates the trade proposal from its own perspective.
Jurors have VETO power — if any juror votes against, the trade is blocked.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class Verdict:
    """A juror's decision on a proposed trade."""
    juror: str
    approved: bool
    reason: str
    warnings: List[str] = field(default_factory=list)
    required_adjustments: List[str] = field(default_factory=list)


class BaseJuror(ABC):
    name: str = "base"

    @abstractmethod
    def judge(self, proposal: dict) -> Verdict:
        """Evaluate a proposed trade and return a Verdict."""

    def __repr__(self) -> str:
        return "<Juror " + self.name + ">"
