"""Historical Loader - Binance klines with disk caching.

Ported from HFT_Brain into QSC. Self-contained, uses utils.logger.
Caches to data/raw/<symbol>_<tf>_<limit>.json.
"""
import asyncio
import json
from pathlib import Path
from typing import List, Optional

import httpx
from loguru import logger


CACHE_DIR = Path("data/raw")


class HistoricalLoader:
    def __init__(
        self,
        base_url: str = "https://api.binance.com",
        symbol: str = "BTCUSDT",
        use_cache: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.symbol = symbol.upper()
        self.use_cache = use_cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, timeframe: str, limit: int) -> Path:
        return CACHE_DIR / f"{self.symbol}_{timeframe}_{limit}.json"

    def _load_from_cache(self, timeframe: str, limit: int) -> Optional[List[dict]]:
        path = self._cache_path(timeframe, limit)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            logger.info(f"HistoricalLoader: loaded {len(data)} cached {timeframe} candles")
            return data
        except Exception as e:
            logger.warning(f"HistoricalLoader: cache read failed: {e}")
            return None

    def _save_to_cache(self, timeframe: str, limit: int, candles: List[dict]) -> None:
        path = self._cache_path(timeframe, limit)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(candles, f)
            logger.info(f"HistoricalLoader: saved {len(candles)} {timeframe} candles to cache")
        except Exception as e:
            logger.error(f"HistoricalLoader: cache write failed: {e}")

    async def _fetch_chunk(
        self,
        client: httpx.AsyncClient,
        timeframe: str,
        limit: int,
        end_time: Optional[int] = None,
    ) -> List[dict]:
        params = {
            "symbol": self.symbol,
            "interval": timeframe,
            "limit": min(limit, 1000),
        }
        if end_time:
            params["endTime"] = end_time

        url = f"{self.base_url}/api/v3/klines"
        r = await client.get(url, params=params)
        r.raise_for_status()
        raw = r.json()

        candles = []
        for row in raw:
            candles.append({
                "open_time": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "close_time": int(row[6]),
                "trades": int(row[8]),
            })
        return candles

    async def fetch_klines(
        self,
        timeframe: str = "1m",
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        force_refresh: bool = False,
    ) -> List[dict]:
        # Check cache first
        if self.use_cache and not force_refresh and start_time is None and end_time is None:
            cached = self._load_from_cache(timeframe, limit)
            if cached is not None and len(cached) >= limit * 0.9:
                return cached

        logger.info(f"HistoricalLoader: fetching {limit} {timeframe} klines for {self.symbol}")
        all_candles: List[dict] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            remaining = limit
            current_end = end_time
            while remaining > 0:
                chunk_size = min(remaining, 1000)
                chunk = await self._fetch_chunk(client, timeframe, chunk_size, current_end)
                if not chunk:
                    break
                all_candles = chunk + all_candles
                remaining -= len(chunk)
                if len(chunk) < chunk_size:
                    break
                current_end = chunk[0]["open_time"] - 1
                await asyncio.sleep(0.1)

        # Deduplicate + sort
        seen = set()
        unique = []
        for c in all_candles:
            if c["open_time"] not in seen:
                seen.add(c["open_time"])
                unique.append(c)
        unique.sort(key=lambda x: x["open_time"])

        if self.use_cache and start_time is None and end_time is None:
            self._save_to_cache(timeframe, limit, unique)

        logger.success(f"HistoricalLoader: fetched {len(unique)} {timeframe} candles")
        return unique

    async def fetch_multi(self, timeframes: List[str], limit: int = 1000) -> dict:
        tasks = {tf: self.fetch_klines(tf, limit) for tf in timeframes}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            tf: (res if not isinstance(res, Exception) else [])
            for tf, res in zip(tasks.keys(), results)
        }
