"""
Binance live WebSocket feed for crypto (BTC, ETH).
No API key required. Falls back to REST polling if websockets package is missing.
"""
import json
import threading
import time
from typing import Dict, List, Optional

from feeds.base_feed import BaseFeed, PriceUpdate


class BinanceFeed(BaseFeed):
    name = "binance"

    WS_URL = "wss://stream.binance.com:9443/stream?streams="
    REST_URL = "https://api.binance.com/api/v3/ticker/price"

    def __init__(self, symbols: Optional[List[str]] = None, poll_seconds: float = 5.0):
        super().__init__()
        self.symbol_map = {
            "BTCUSD": "BTCUSDT",
            "ETHUSD": "ETHUSDT",
        }
        self.symbols = symbols or list(self.symbol_map.keys())
        self.poll_seconds = poll_seconds
        self._thread = None
        self._stop_flag = False

    def _build_stream_url(self) -> str:
        streams = []
        for sym in self.symbols:
            binance_sym = self.symbol_map.get(sym, sym)
            streams.append(binance_sym.lower() + "@bookTicker")
        return self.WS_URL + "/".join(streams)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
        self._running = False

    def _run_forever(self) -> None:
        try:
            import websockets  # noqa: F401
            import asyncio
            asyncio.run(self._ws_loop())
        except ImportError:
            print("BinanceFeed: websockets not installed, using REST polling")
            self._rest_loop()
        except Exception as e:
            print("BinanceFeed: WS failed (" + str(e) + "), using REST")
            self._rest_loop()

    async def _ws_loop(self) -> None:
        import websockets
        url = self._build_stream_url()
        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            while not self._stop_flag:
                try:
                    raw = await ws.recv()
                    self._handle_message(json.loads(raw))
                except Exception as e:
                    print("BinanceFeed WS error:", e)
                    break

    def _handle_message(self, data: dict) -> None:
        payload = data.get("data") or data
        sym_raw = (payload.get("s") or "").upper()
        for our, binance_sym in self.symbol_map.items():
            if binance_sym == sym_raw:
                bid = float(payload.get("b") or 0)
                ask = float(payload.get("a") or 0)
                last = (bid + ask) / 2.0 if bid and ask else bid or ask
                self._emit(PriceUpdate(symbol=our, bid=bid, ask=ask, last=last, source="binance_ws"))
                return

    def _rest_loop(self) -> None:
        import urllib.request
        while not self._stop_flag:
            try:
                req = urllib.request.Request(self.REST_URL)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    arr = json.loads(resp.read().decode())
                    by_sym = {item["symbol"]: item["price"] for item in arr}
                    for our, binance_sym in self.symbol_map.items():
                        if our not in self.symbols:
                            continue
                        p = by_sym.get(binance_sym)
                        if p:
                            price = float(p)
                            self._emit(PriceUpdate(symbol=our, bid=price, ask=price, last=price, source="binance_rest"))
            except Exception as e:
                print("BinanceFeed REST error:", e)
            time.sleep(self.poll_seconds)
