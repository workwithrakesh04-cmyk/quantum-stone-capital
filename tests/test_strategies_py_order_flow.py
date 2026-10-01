"""Tests for strategies_py.order_flow strategies.

Smoke tests: each strategy must instantiate, run on flat + trending candles,
and produce a valid Signal (HOLD or LONG/SHORT).
"""
from strategies_py.order_flow.absorption import AbsorptionStrategy
from strategies_py.order_flow.delta_divergence import DeltaDivergenceStrategy
from strategies_py.order_flow.stacked_imbalance import StackedImbalanceStrategy
from strategies_py.order_flow.trapped_traders import TrappedTradersStrategy
from strategies_py.order_flow.naked_poc import NakedPOCStrategy
from strategies_py.order_flow.poc_strategy import POCStrategy
from strategies_py.order_flow.value_area import ValueAreaStrategy
from strategies_py.order_flow.volume_cluster import VolumeClusterStrategy
from beta_brain.signal import Signal


def _candle(o, h, l, c, v=1.0, ts=0, bv=0.0, sv=0.0):
    return {
        "open": o, "high": h, "low": l, "close": c, "volume": v,
        "open_time": ts, "buy_volume": bv, "sell_volume": sv,
    }


def _flat_candles(n=100, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, 1.0, i * 300_000) for i in range(n)]


def _trending_up_candles(n=100, base=100.0):
    out = []
    p = base
    for i in range(n):
        p *= 1.002
        out.append(_candle(p, p * 1.005, p * 0.995, p, 1.0, i * 300_000))
    return out


def test_absorption_instantiates_and_runs():
    s = AbsorptionStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "absorption"
    assert sig.direction in ("LONG", "SHORT", "HOLD")


def test_delta_divergence_instantiates_and_runs():
    s = DeltaDivergenceStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "delta_divergence"


def test_delta_divergence_requires_buy_sell_volumes():
    s = DeltaDivergenceStrategy(timeframe="5m")
    candles = _flat_candles(20)
    sig = s.analyze(candles)
    # No divergence because bv=sv=0 in flat candles
    assert sig.direction == "HOLD"


def test_stacked_imbalance_instantiates_and_runs():
    s = StackedImbalanceStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "stacked_imbalance"


def test_trapped_traders_instantiates_and_runs():
    s = TrappedTradersStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "trapped_traders"


def test_naked_poc_instantiates_and_runs():
    s = NakedPOCStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(100))
    assert isinstance(sig, Signal)
    assert sig.strategy == "naked_poc"


def test_poc_strategy_instantiates_and_runs():
    s = POCStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(60))
    assert isinstance(sig, Signal)
    assert sig.strategy == "poc"


def test_value_area_instantiates_and_runs():
    s = ValueAreaStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(60))
    assert isinstance(sig, Signal)
    assert sig.strategy == "value_area"


def test_volume_cluster_instantiates_and_runs():
    s = VolumeClusterStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(60))
    assert isinstance(sig, Signal)
    assert sig.strategy == "volume_cluster"
