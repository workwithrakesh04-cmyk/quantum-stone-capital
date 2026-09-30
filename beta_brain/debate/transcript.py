"""Debate Transcript schema - shared across Beta Brain debate bots."""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import json


@dataclass
class Argument:
    bot: str                                    # "BUY" | "SELL" | "HOLD"
    round: int                                  # 1, 2, 3
    confidence: float
    statement: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    rebuttals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DebateTranscript:
    ts: int
    symbol: str
    timeframe: str
    signals_input: List[Dict[str, Any]]
    rounds: List[List[Argument]]
    winner: str                                 # "BUY" | "SELL" | "HOLD"
    winner_confidence: float
    final_scores: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signals_input": self.signals_input,
            "rounds": [[a.to_dict() for a in rnd] for rnd in self.rounds],
            "winner": self.winner,
            "winner_confidence": self.winner_confidence,
            "final_scores": self.final_scores,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)
