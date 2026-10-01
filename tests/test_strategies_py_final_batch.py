"""Tests for the final 19 strategies (ICT/SMC + patterns + ML + volatility + trend)."""
from strategies_py.ict_smc.fvg_strategy import FVGStrategy
from strategies_py.ict_smc.luxalgo_fvg import LuxAlgoFVGStrategy
from strategies_py.patterns.diamond_cancan import DiamondCanCanStrategy
from strategies_py.patterns.head_shoulders import HeadShouldersStrategy
from strategies_py.patterns.double_top_bottom import DoubleTopBottomStrategy
from strategies_py.patterns.engulfing_pinbar import EngulfingPinBarStrategy
from strategies_py.patterns.reversal_123 import Reversal123Strategy
from strategies_py.ml_adaptive.adaptive_rsi_ml import AdaptiveRSIMLStrategy
from strategies_py.ml_adaptive.ai_source_ma import AISourceMAStrategy
from strategies_py.ml_adaptive.ai_trend_flow import AITrendFlowStrategy
from strategies_py.ml_adaptive.ml_momentum import MLMomentumStrategy
from strategies_py.ml_adaptive.ml_rsi import MLRSIStrategy
from strategies_py.volatility.mad_loop_bb import MADBollingerStrategy
from strategies_py.volatility.mad_loop_fl import MADForLoopStrategy
from strategies_py.volatility.mad_loop_combined import MADCombinedStrategy
from strategies_py.volatility.apex_flow import ApexFlowStrategy
from strategies_py.volatility.rmd_trail import RMDTrailStrategy
from strategies_py.trend.ichimoku_rsi import IchimokuRSIStrategy
from strategies_py.trend.cardwell_rsi import CardwellRSIStrategy
from strategies_py.trend.intermarket import IntermarketStrategy
from beta_brain.signal import Signal


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": 1.0, "open_time": ts}


def _flat_candles(n=150, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, i * 300_000) for i in range(n)]


def test_fvg_instantiates_and_runs():
    s = FVGStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "fvg"


def test_luxalgo_fvg_instantiates_and_runs():
    s = LuxAlgoFVGStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "luxalgo_fvg"


def test_diamond_cancan_instantiates_and_runs():
    s = DiamondCanCanStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "diamond_cancan"


def test_head_shoulders_instantiates_and_runs():
    s = HeadShouldersStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "head_shoulders"


def test_double_top_bottom_instantiates_and_runs():
    s = DoubleTopBottomStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "double_top_bottom"


def test_engulfing_pinbar_instantiates_and_runs():
    s = EngulfingPinBarStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "engulfing_pinbar"


def test_reversal_123_instantiates_and_runs():
    s = Reversal123Strategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "reversal_123"


def test_adaptive_rsi_ml_instantiates_and_runs():
    s = AdaptiveRSIMLStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "adaptive_rsi_ml"


def test_ai_source_ma_instantiates_and_runs():
    s = AISourceMAStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "ai_source_ma"


def test_ai_trend_flow_instantiates_and_runs():
    s = AITrendFlowStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "ai_trend_flow"


def test_ml_momentum_instantiates_and_runs():
    s = MLMomentumStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "ml_momentum"


def test_ml_rsi_instantiates_and_runs():
    s = MLRSIStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "ml_rsi"


def test_mad_bb_instantiates_and_runs():
    s = MADBollingerStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "mad_bb"


def test_mad_fl_instantiates_and_runs():
    s = MADForLoopStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "mad_fl"


def test_mad_combined_instantiates_and_runs():
    s = MADCombinedStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "mad_combined"


def test_apex_flow_instantiates_and_runs():
    s = ApexFlowStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "apex_flow"


def test_rmd_trail_instantiates_and_runs():
    s = RMDTrailStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "rmd_trail"


def test_ichimoku_rsi_instantiates_and_runs():
    s = IchimokuRSIStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "ichimoku_rsi"


def test_cardwell_rsi_instantiates_and_runs():
    s = CardwellRSIStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "cardwell_rsi"


def test_intermarket_instantiates_and_runs():
    s = IntermarketStrategy(timeframe="5m")
    sig = s.analyze(_flat_candles())
    assert isinstance(sig, Signal)
    assert sig.strategy == "intermarket"
