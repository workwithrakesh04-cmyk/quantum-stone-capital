import yaml
from pathlib import Path

config = {
    "project": {
        "name": "Quantum Stone Capital - HFT AI Brain",
        "version": "0.1.0",
        "mode": "backtest",
    },
    "accounts": {
        "personal": {
            "capital": 10000,
            "max_risk_per_trade": 0.01,
            "max_daily_loss": 0.03,
            "max_drawdown": 0.10,
            "max_concurrent_positions": 5,
            "instruments": ["BTCUSD", "XAUUSD", "EURUSD", "GBPUSD"],
        },
        "prop": {
            "firm": "TBD",
            "capital": 10000,
            "max_risk_per_trade": 0.01,
            "max_daily_loss": 0.05,
            "max_drawdown": 0.10,
            "consistency_rule": 0.30,
            "news_trading": False,
            "weekend_holding": False,
            "min_trading_days": 0,
        },
    },
    "assets": {
        "BTCUSD": {
            "type": "crypto",
            "yield_type": "zero_income",
            "storage_cost": 0.0,
            "convenience_yield": 0.0,
            "timeframe_primary": "5m",
            "timeframe_bias": "4h",
        },
        "XAUUSD": {
            "type": "commodity",
            "yield_type": "investment_commodity",
            "storage_cost": 0.001,
            "convenience_yield": 0.0,
            "timeframe_primary": "5m",
            "timeframe_bias": "4h",
        },
        "EURUSD": {
            "type": "forex",
            "yield_type": "foreign_rate_yield",
            "foreign_rate_source": "ESTER",
            "timeframe_primary": "5m",
            "timeframe_bias": "4h",
        },
        "GBPUSD": {
            "type": "forex",
            "yield_type": "foreign_rate_yield",
            "foreign_rate_source": "SONIA",
            "timeframe_primary": "5m",
            "timeframe_bias": "4h",
        },
    },
    "microstructure": {
        "kyle_lambda": {"enabled": True, "sigma_u_default": 1.0},
        "bayesian_fair_value": {"enabled": True},
        "signal_filter": {"min_z_score": 1.5, "extreme_only": True},
        "order_impact": {"max_impact_pct": 0.001, "twap_threshold_pct": 0.0005},
    },
    "risk": {
        "hedge_ratio_formula": "h* = rho * sigma_S / sigma_F",
        "var_confidence": 0.95,
        "var_horizon_days": 1,
        "var_method": "historical",
        "max_risk_per_trade": 0.01,
        "min_rr_ratio": 2.0,
        "max_losses_per_day": 2,
    },
    "execution": {
        "order_types": ["market", "limit", "stop", "stop_limit", "mit", "fok", "gtc"],
        "margin_model": {
            "initial_margin_pct": 0.02,
            "maintenance_margin_pct": 0.015,
            "auto_liquidate_threshold": 0.015,
        },
        "slippage_model": "linear",
        "max_slippage_pct": 0.001,
    },
    "strategies": {"min_confluence_score": 0.65, "active": []},
    "wyckoff": {"enabled": True, "min_nine_tests": 7},
    "smc": {"enabled": True, "require_bos_or_choch": True},
    "vpa": {"enabled": True, "require_validation": True},
    "market_profile": {"enabled": True, "min_confidence": 0.65},
    "elliott_wave": {
        "enabled": True,
        "fib_ratios": {
            "retracement": [0.236, 0.382, 0.5, 0.618, 0.786],
            "extension": [1.0, 1.272, 1.618, 2.618],
        },
    },
    "ml": {
        "framework": "pytorch",
        "device": "cpu",
        "models": ["xgboost", "lightgbm", "ppo"],
        "alpha_factors": ["momentum", "value", "quality", "volatility"],
    },
    "reference_rates": {
        "USD": "SOFR", "GBP": "SONIA", "EUR": "ESTER",
        "CHF": "SARON", "JPY": "TONAR",
        "fetch_frequency": "daily",
    },
    "logging": {"level": "INFO", "file": "logs/bot.log", "console": True},
    "github": {"commit_every_phase": True, "branch": "main"},
}

path = Path("config/master.yaml")
with path.open("w", encoding="utf-8") as f:
    yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False, indent=2)

print(f"✅ Wrote {path} ({path.stat().st_size} bytes)")
