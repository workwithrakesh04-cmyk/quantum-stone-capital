import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

# Generate 500 synthetic 5-minute bars for BTCUSD
n = 500
start = pd.Timestamp("2024-01-01", tz="UTC")
times = pd.date_range(start=start, periods=n, freq="5min")

# Random walk price
close = 40000 + np.cumsum(np.random.randn(n) * 50)
high = close + np.abs(np.random.randn(n) * 30)
low = close - np.abs(np.random.randn(n) * 30)
open_ = np.roll(close, 1)
open_[0] = close[0]
volume = np.random.randint(500, 5000, n).astype(float)

df = pd.DataFrame({
    "timestamp": times,
    "open": open_,
    "high": np.maximum.reduce([open_, close, high]),
    "low": np.minimum.reduce([open_, close, low]),
    "close": close,
    "volume": volume,
})

Path("data/raw").mkdir(parents=True, exist_ok=True)
df.to_csv("data/raw/BTCUSD_5m.csv", index=False)
print(f"OK: wrote data/raw/BTCUSD_5m.csv ({len(df)} bars)")
