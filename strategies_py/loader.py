"""Loader - auto-discovers all Beta strategies and returns classes."""
from typing import List, Type
import importlib
import inspect
from loguru import logger

from strategies_py.base import BaseStrategy


_STRATEGY_MODULES = [
    # Order flow (5a-2)
    "strategies_py.order_flow.absorption",
    "strategies_py.order_flow.delta_divergence",
    "strategies_py.order_flow.stacked_imbalance",
    "strategies_py.order_flow.trapped_traders",
    "strategies_py.order_flow.naked_poc",
    "strategies_py.order_flow.poc_strategy",
    "strategies_py.order_flow.value_area",
    "strategies_py.order_flow.volume_cluster",
    # Liquidity (5a-3)
    "strategies_py.liquidity.liquidity_sweep",
    "strategies_py.liquidity.false_breakout",
    "strategies_py.liquidity.bs_ss_liquidity",
    "strategies_py.liquidity.turtle_soup",
    "strategies_py.liquidity.quasimodo",
    # Supply/demand (5a-3)
    "strategies_py.supply_demand.rbd_dbr",
    "strategies_py.supply_demand.sd_zones",
    "strategies_py.supply_demand.ftr_compression",
    "strategies_py.supply_demand.flag_limits",
    "strategies_py.supply_demand.three_drive",
    # ICT/SMC (5a-4)
    "strategies_py.ict_smc.fvg_strategy",
    "strategies_py.ict_smc.luxalgo_fvg",
    # Patterns (5a-4)
    "strategies_py.patterns.diamond_cancan",
    "strategies_py.patterns.head_shoulders",
    "strategies_py.patterns.double_top_bottom",
    "strategies_py.patterns.engulfing_pinbar",
    "strategies_py.patterns.reversal_123",
    # ML (5a-4)
    "strategies_py.ml_adaptive.adaptive_rsi_ml",
    "strategies_py.ml_adaptive.ai_source_ma",
    "strategies_py.ml_adaptive.ai_trend_flow",
    "strategies_py.ml_adaptive.ml_momentum",
    "strategies_py.ml_adaptive.ml_rsi",
    # Volatility (5a-4)
    "strategies_py.volatility.mad_loop_bb",
    "strategies_py.volatility.mad_loop_fl",
    "strategies_py.volatility.mad_loop_combined",
    "strategies_py.volatility.apex_flow",
    "strategies_py.volatility.rmd_trail",
    # Trend (5a-4)
    "strategies_py.trend.ichimoku_rsi",
    "strategies_py.trend.cardwell_rsi",
    "strategies_py.trend.intermarket",
]


def load_all_strategies() -> List[Type[BaseStrategy]]:
    """Return list of all BaseStrategy subclasses found in known modules.
    Modules that don't exist yet (later deliveries) are skipped silently."""
    classes: List[Type[BaseStrategy]] = []
    for mod_name in _STRATEGY_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"strategies_py.loader: import {mod_name} failed: {e}")
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj is BaseStrategy:
                continue
            if issubclass(obj, BaseStrategy) and obj.__module__ == mod_name:
                classes.append(obj)

    seen = set()
    unique: List[Type[BaseStrategy]] = []
    for c in classes:
        if c.NAME in seen:
            continue
        seen.add(c.NAME)
        unique.append(c)

    logger.info(f"strategies_py.loader: loaded {len(unique)} strategy classes")
    return unique
