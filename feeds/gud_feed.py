"""
gud-price feed — reads Chainlink oracle price feeds on Ethereum.
Free, no API keys. Poll-based reads of on-chain contract state.
Covers: BTC, ETH, SOL, EUR/USD, GBP/USD, XAU (Gold), XAG (Silver), SPY.
"""
import threading
import time
from typing import Callable, Dict, List, Optional

from feeds.base_feed import BaseFeed, PriceUpdate


class GudPriceFeed(BaseFeed):
    name = "gud-price"

    SYMBOL_MAP = {
        "BTCUSD":  "BTC_USD",
        "ETHUSD":  "ETH_USD",
        "SOLUSD":  "SOL_USD",
        "EURUSD":  "EUR_USD",
        "GBPUSD":  "GBP_USD",
        "XAUUSD":  "XAU_USD",
        "XAGUSD":  "XAG_USD",
        "SPY":     "SPY_USD_24_5",
        "JPYUSD":  "JPY_USD",
        "CHFUSD":  "CHF_USD",
        "AUDUSD":  "AUD_USD",
        "CADUSD":  "CAD_USD",
    }

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        poll_seconds: float = 10.0,
    ):
        super().__init__()
        self.symbols = symbols or ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "XAUUSD"]
        self.poll_seconds = poll_seconds
        self._thread = None
        self._stop_flag = False
        self._fetchers: Dict[str, Callable] = {}

    def _resolve_feeds(self) -> bool:
        try:
            import gud_price.ethereum as eth
            from gud_price.rpc import read_latest_price
        except ImportError:
            print("GudPriceFeed: pip install gud-price")
            return False

        for our_sym in self.symbols:
            const_name = self.SYMBOL_MAP.get(our_sym)
            if const_name is None:
                print("GudPriceFeed: unknown symbol " + our_sym)
                continue
            feed_const = getattr(eth, const_name, None)
            if feed_const is None:
                print("GudPriceFeed: no constant " + const_name + " for " + our_sym)
                continue
            self._fetchers[our_sym] = (feed_const, read_latest_price)
        return len(self._fetchers) > 0

    def start(self) -> None:
        if not self._resolve_feeds():
            print("GudPriceFeed: no fetchers resolved, aborting start")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
        self._running = False

    def _fetch_one(self, symbol: str) -> Optional[float]:
        entry = self._fetchers.get(symbol)
        if entry is None:
            return None
        feed_const, reader = entry
        try:
            data = reader(feed_const)
            return float(data.answer)
        except Exception as e:
            print("GudPrice error [" + symbol + "]: " + type(e).__name__ + " " + str(e))
            return None

    def _run_forever(self) -> None:
        # Immediate first pass
        for sym in self.symbols:
            if self._stop_flag:
                return
            price = self._fetch_one(sym)
            if price is not None:
                self._emit(PriceUpdate(symbol=sym, bid=price, ask=price, last=price, source="gud-price"))
            time.sleep(0.3)

        # Then poll periodically
        while not self._stop_flag:
            time.sleep(self.poll_seconds)
            for sym in self.symbols:
                if self._stop_flag:
                    return
                price = self._fetch_one(sym)
                if price is not None:
                    self._emit(PriceUpdate(symbol=sym, bid=price, ask=price, last=price, source="gud-price"))
                time.sleep(0.3)
