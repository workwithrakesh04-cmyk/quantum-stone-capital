"""
Biquote live feed (official Python client).
pip install biquote
Returns: bq.latest([syms]) -> {sym: {bid, ask, mid, last, stale, marketState, ...}}
"""
import threading
import time
from typing import List, Optional

from feeds.base_feed import BaseFeed, PriceUpdate


class BiquoteFeed(BaseFeed):
    name = "biquote"

    def __init__(self, symbols: Optional[List[str]] = None, poll_seconds: float = 3.0):
        super().__init__()
        self.symbols = symbols or ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "ETHUSD"]
        self.poll_seconds = poll_seconds
        self._thread = None
        self._stop_flag = False
        self._bq = None

    def start(self) -> None:
        try:
            from biquote import Biquote
            self._bq = Biquote()
        except ImportError:
            print("BiquoteFeed: pip install biquote")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
        self._running = False

    def _emit_from_dict(self, sym: str, d: dict) -> None:
        """Convert biquote tick dict -> PriceUpdate."""
        if not isinstance(d, dict):
            return
        bid = float(d.get("bid") or 0)
        ask = float(d.get("ask") or 0)
        mid = float(d.get("mid") or 0)
        last = float(d.get("last") or 0)
        # Prefer mid, fall back to bid/ask average, then last
        price = mid if mid > 0 else ((bid + ask) / 2.0 if bid > 0 and ask > 0 else last)
        if price <= 0:
            return
        self._emit(PriceUpdate(
            symbol=sym,
            bid=bid or price,
            ask=ask or price,
            last=price,
            source="biquote",
        ))

    def _run_forever(self) -> None:
        while not self._stop_flag:
            try:
                data = self._bq.latest(self.symbols)
                if isinstance(data, dict):
                    # {sym: {bid, ask, mid, ...}}
                    for sym, payload in data.items():
                        self._emit_from_dict(sym, payload)
                elif isinstance(data, list):
                    # [{symbol, bid, ask, mid, ...}, ...]
                    for item in data:
                        if isinstance(item, dict):
                            self._emit_from_dict(item.get("symbol", ""), item)
            except Exception as e:
                print("BiquoteFeed error:", e)
            time.sleep(self.poll_seconds)
