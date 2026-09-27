"""
MarketContext: the single input shape that flows through every layer.
Any data feed (MT5, CSV, live) must produce this and hand it to the Main Brain.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MarketContext:
    # Identity
    symbol: str
    timeframe: str
    timestamp: Optional[str] = None

    # OHLCV history (most recent last)
    closes: List[float] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    opens: List[float] = field(default_factory=list)
    volumes: List[float] = field(default_factory=list)

    # Pre-computed features (optional — filled by feature layer)
    momentum: Optional[float] = None
    rsi: Optional[float] = None
    delta: Optional[float] = None
    volatility: Optional[float] = None
    bos: Optional[str] = None  # "BOS_BULLISH" | "BOS_BEARISH" | "CHOCH_*" | None

    # Regime and session
    regime: Optional[str] = None  # "trending_up" | "trending_down" | "ranging" | "volatile"
    session: Optional[str] = None  # "tokyo" | "london" | "new_york" | "off_hours"
    active_killzones: List[str] = field(default_factory=list)
    is_weekend: bool = False

    # Market microstructure
    is_illiquid: bool = False
    kyle_lambda: Optional[float] = None

    # Signal filter
    passes_filter: bool = False
    signal_score: float = 0.0

    # Framework agreement flags (optional — set by caller or higher layers)
    agreeing_frameworks: List[str] = field(default_factory=list)
    harmonic_bullish: bool = False
    harmonic_bearish: bool = False
    wave3_active: bool = False
    wave_c_active: bool = False

    # Extra metadata
    meta: Dict = field(default_factory=dict)

    @property
    def last_price(self) -> Optional[float]:
        return self.closes[-1] if self.closes else None

    @property
    def is_valid(self) -> bool:
        return bool(self.closes) and self.symbol != ""
