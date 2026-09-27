"""
Yahoo Finance feed (no API key, no signup).
Covers indices: NASDAQ (^IXIC, ^NDX), S&P 500 (^GSPC), Dow (^DJI).
Uses the public Yahoo Finance chart API — no package needed.
Data is ~15-min delayed for free access; fine for our purposes.
"""
import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from feeds.base_feed import BaseFeed, PriceUpdate


class YahooFeed(BaseFeed):
    name = "yahoo"

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"

    # our symbol -> Yahoo ticker
    SYMBOL_MAP = {
        "NASDAQ":  "^IXIC",    # Nasdaq Composite
        "NAS100":  "^NDX",     # Nasdaq 100
        "SPX500":  "^GSPC",    # S&P 500
        "US30":    "^DJI",     # Dow Jones
        "DAX":     "^GDAXI",   # German DAX
        "NIKKEI":  "^N225",    # Nikkei 225
    }

    # Yahoo needs a browser-like User-Agent, else 401/429
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0 Safari/537.36",
        "Accept": "application/json",
    }

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        poll_seconds: float = 15.0,
    ):
        super().__init__()
        self.symbols = symbols or ["NASDAQ", "NAS100", "SPX500"]
        self.poll_seconds = poll_seconds
        self._thread = None
        self._stop_flag = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
        self._running = False

    def _fetch_quote(self, our_symbol: str) -> Optional[float]:
        yahoo_sym = self.SYMBOL_MAP.get(our_symbol)
        if yahoo_sym is None:
            return None
        url = self.BASE_URL + urllib.parse.quote(yahoo_sym) + "?range=1d&interval=1m"
        try:
            req = urllib.request.Request(url, headers=self.HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            result = data.get("chart", {}).get("result") or []
            if not result:
                return None
            meta = result[0].get("meta", {})
            price = float(meta.get("regularMarketPrice") or 0)
            return price if price > 0 else None
        except Exception as e:
            print("Yahoo error [" + our_symbol + "]: " + str(e))
            return None

    def _run_forever(self) -> None:
        while not self._stop_flag:
            for sym in self.symbols:
                if self._stop_flag:
                    break
                price = self._fetch_quote(sym)
                if price is None:
                    continue
                self._emit(PriceUpdate(
                    symbol=sym, bid=price, ask=price, last=price,
                    source="yahoo",
                ))
                time.sleep(1.0)  # polite: 1s between calls
            time.sleep(self.poll_seconds)
