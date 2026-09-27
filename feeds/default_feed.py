"""
Default feed aggregator — combines Binance (crypto streaming) +
gud-price (Chainlink oracles for FX/Gold/SPY) + Biquote (backup).
"""
from feeds.binance_feed import BinanceFeed
from feeds.gud_feed import GudPriceFeed
from feeds.biquote_feed import BiquoteFeed
from feeds.aggregator import FeedAggregator


def build_default_aggregator(
    cryptos=None,
    fx_gold_index=None,
    backup_symbols=None,
) -> FeedAggregator:
    cryptos = cryptos or ["BTCUSD", "ETHUSD"]
    fx_gold_index = fx_gold_index or ["EURUSD", "GBPUSD", "XAUUSD", "SPY"]
    backup_symbols = backup_symbols or ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "ETHUSD"]

    # Primary: Binance WebSocket for crypto (fastest updates)
    binance = BinanceFeed(symbols=cryptos, poll_seconds=3.0)

    # Primary: gud-price Chainlink oracles for FX, Gold, SPY
    gud = GudPriceFeed(
        symbols=["BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPUSD", "XAUUSD", "SPY"],
        poll_seconds=15.0,
    )

    # Backup: Biquote for FX/Gold (fallback if gud-price is down)
    biquote = BiquoteFeed(symbols=backup_symbols, poll_seconds=5.0)

    return FeedAggregator(feeds=[binance, gud, biquote])
