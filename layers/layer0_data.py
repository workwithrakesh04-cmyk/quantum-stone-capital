"""
Layer 0 — Data.
Abstract data feed interface + CSV replay adapter for offline backtesting.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import pandas as pd


@dataclass
class Bar:
    """A single OHLCV bar."""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str


class DataFeed(ABC):
    """Abstract base class for all data feeds (MT5, Binance, OANDA, CSV, etc.)."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the feed. Return True on success."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection."""

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 500,
    ) -> List[Bar]:
        """Fetch the last `count` bars for a symbol/timeframe."""

    @abstractmethod
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Return the latest bid/mid price."""


class CSVDataFeed(DataFeed):
    """
    CSV-based replay feed for backtesting.
    Expects columns: timestamp, open, high, low, close, volume
    (case-insensitive).
    """

    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self._cache: dict = {}
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._cache.clear()

    def _load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = f"{symbol}_{timeframe}"
        if key in self._cache:
            return self._cache[key]

        path = self.data_dir / f"{symbol}_{timeframe}.csv"
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]

        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns in {path}: {missing}")

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)

        self._cache[key] = df
        return df

    def get_bars(self, symbol: str, timeframe: str, count: int = 500) -> List[Bar]:
        df = self._load(symbol, timeframe)
        tail = df.tail(count)
        return [
            Bar(
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                symbol=symbol,
                timeframe=timeframe,
            )
            for _, row in tail.iterrows()
        ]

    def get_latest_price(self, symbol: str) -> Optional[float]:
        for key, df in self._cache.items():
            if key.startswith(symbol):
                return float(df["close"].iloc[-1])
        return None


class DataFeedFactory:
    """Factory for creating data feeds by name."""

    @staticmethod
    def create(feed_type: str = "csv", **kwargs) -> DataFeed:
        feed_type = feed_type.lower()
        if feed_type == "csv":
            return CSVDataFeed(**kwargs)
        # Phase 3+ will add: "mt5", "binance", "oanda"
        raise ValueError(f"Unknown feed type: {feed_type}")
