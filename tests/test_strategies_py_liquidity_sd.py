"""Tests for strategies_py.liquidity + supply_demand strategies."""
from strategies_py.liquidity.liquidity_sweep import LiquiditySweepStrategy
from strategies_py.liquidity.false_breakout import FalseBreakoutStrategy
from strategies_py.liquidity.bs_ss_liquidity import BuysideSellsideLiquidityStrategy
from strategies_py.liquidity.turtle_soup import TurtleSoupStrategy
from strategies_py.liquidity.quasimodo import QuasimodoStrategy
from strategies_py.supply_demand.rbd_dbr import RBDDBRStrategy
from strategies_py.supply_demand.sd_zones import SDZonesStrategy
from strategies_py.supply_demand.ftr_compression import FTRCompressionStrategy
from strategies_py.supply_demand.flag_limits import FlagLimitsStrategy
from strategies_py.supply_demand.three_drive import ThreeDriveStrategy
from beta_brain.signal import Signal


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1.0, "open_time": ts}


def _flat_candles(n=100, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, i * 300_000) for i in range(n)]


def test_liquidity_sweep_instantiates_and_runs():
    s = LiquiditySweepStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "liquidity_sweep"


def test_false_breakout_instantiates_and_runs():
    s = FalseBreakoutStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "false_breakout"


def test_bs_ss_liquidity_instantiates_and_runs():
    s = BuysideSellsideLiquidityStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(80))
    assert isinstance(sig, Signal)
    assert sig.strategy == "bs_ss_liquidity"


def test_turtle_soup_instantiates_and_runs():
    s = TurtleSoupStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(60))
    assert isinstance(sig, Signal)
    assert sig.strategy == "turtle_soup"


def test_quasimodo_instantiates_and_runs():
    s = QuasimodoStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "quasimodo"


def test_rbd_dbr_instantiates_and_runs():
    s = RBDDBRStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "rbd_dbr"


def test_sd_zones_instantiates_and_runs():
    s = SDZonesStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "sd_zones"


def test_ftr_compression_instantiates_and_runs():
    s = FTRCompressionStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(30))
    assert isinstance(sig, Signal)
    assert sig.strategy == "ftr_compression"


def test_flag_limits_instantiates_and_runs():
    s = FlagLimitsStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "flag_limits"


def test_three_drive_instantiates_and_runs():
    s = ThreeDriveStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles(20))
    assert isinstance(sig, Signal)
    assert sig.strategy == "three_drive"
