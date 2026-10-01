"""Smoke tests for BetaBacktester + reporter."""
from backtest.beta_backtester import BetaBacktester, BacktestResult
from backtest.reporter import (
    format_metrics_block, format_strategy_table, format_regime_table,
    build_full_report,
)


def _candle(o, h, l, c, v=1.0, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v, "open_time": ts}


def _flat_candles(n=300, base=100.0):
    return [_candle(base, base * 1.005, base * 0.995, base, 1.0, i * 300_000) for i in range(n)]


def _trending_up_candles(n=300, base=100.0):
    out = []
    p = base
    for i in range(n):
        p *= 1.001
        out.append(_candle(p, p * 1.002, p * 0.999, p, 1.0, i * 300_000))
    return out


def test_backtester_initializes():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50)
    assert bt.symbol == "BTCUSDT"
    assert bt.warmup == 50


def test_backtester_runs_on_flat_candles():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50, max_window=100)
    candles = _flat_candles(300)
    result = bt.run_on_candles(candles)
    assert isinstance(result, BacktestResult)
    assert result.total_candles == 300
    assert result.warmup == 50


def test_backtester_runs_on_trending_candles():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50, max_window=100)
    candles = _trending_up_candles(300)
    result = bt.run_on_candles(candles)
    assert result.total_candles == 300


def test_backtester_raises_on_short_history():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=100)
    candles = _flat_candles(50)
    try:
        bt.run_on_candles(candles)
        assert False, "should have raised"
    except ValueError:
        assert True


def test_backtester_returns_valid_stats():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50, max_window=100)
    result = bt.run_on_candles(_flat_candles(300))
    s = result.stats
    assert "starting_balance" in s
    assert "ending_balance" in s
    assert "net_pnl" in s
    assert "total_trades" in s


def test_backtester_diagnostics():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50, max_window=100)
    bt.run_on_candles(_flat_candles(300))
    d = bt.get_diagnostics()
    assert "candles_processed" in d
    assert d["candles_processed"] > 0


def test_backtester_analyzer_dict():
    bt = BetaBacktester(symbol="BTCUSDT", timeframe="5m", warmup=50, max_window=100)
    bt.run_on_candles(_flat_candles(300))
    ad = bt.get_analyzer_dict()
    assert "strategies" in ad
    assert "regimes" in ad
    assert "directions" in ad


def test_format_metrics_block():
    result = {
        "stats": {
            "starting_balance": 10000, "ending_balance": 10500,
            "net_pnl": 500, "return_pct": 5.0, "peak_balance": 10600,
            "max_drawdown_usd": 100, "max_drawdown_pct": 0.94,
            "total_trades": 20, "wins": 12, "losses": 8, "flat": 0,
            "win_rate": 60.0, "profit_factor": 1.5,
            "avg_win": 50.0, "avg_loss": -30.0,
            "expectancy_usd": 25.0,
            "sharpe": 1.5, "sortino": 2.0, "calmar": 3.0,
            "exits_tp": 8, "exits_sl": 6, "exits_timeout": 6, "exits_eod": 0,
        },
        "start_iso": "2026-01-01T00:00:00Z",
        "end_iso": "2026-02-01T00:00:00Z",
        "total_candles": 10000, "warmup": 100, "runtime_sec": 120.0,
    }
    text = format_metrics_block(result, "BTCUSDT", "5m")
    assert "BETA BRAIN BACKTEST" in text
    assert "BTCUSDT" in text


def test_format_strategy_table_empty():
    text = format_strategy_table({"strategies": {}})
    assert "no trades" in text


def test_format_strategy_table_populated():
    ad = {"strategies": {
        "false_breakout": {"trades": 10, "wins": 6, "losses": 4,
                           "win_rate": 60.0, "net_pnl": 100.0, "avg_pnl_per_trade": 10.0},
        "volume_cluster": {"trades": 5, "wins": 2, "losses": 3,
                           "win_rate": 40.0, "net_pnl": -50.0, "avg_pnl_per_trade": -10.0},
    }}
    text = format_strategy_table(ad)
    assert "false_breakout" in text
    assert "volume_cluster" in text


def test_format_regime_table_populated():
    ad = {"regimes": {
        "RANGING": {"a": {"trades": 5, "wins": 3, "net_pnl": 50.0}},
        "TRENDING_UP": {"b": {"trades": 3, "wins": 1, "net_pnl": -20.0}},
    }}
    text = format_regime_table(ad)
    assert "RANGING" in text
    assert "TRENDING_UP" in text


def test_build_full_report():
    result = {
        "stats": {
            "starting_balance": 10000, "ending_balance": 10000,
            "net_pnl": 0, "return_pct": 0, "peak_balance": 10000,
            "max_drawdown_usd": 0, "max_drawdown_pct": 0,
            "total_trades": 0, "wins": 0, "losses": 0, "flat": 0,
            "win_rate": 0, "profit_factor": 0,
            "avg_win": 0, "avg_loss": 0,
            "exits_tp": 0, "exits_sl": 0, "exits_timeout": 0, "exits_eod": 0,
        },
        "start_iso": "x", "end_iso": "y", "total_candles": 100,
        "warmup": 50, "runtime_sec": 1.0,
    }
    text = build_full_report(result, {"strategies": {}, "regimes": {}}, "BTCUSDT", "5m")
    assert "HEADLINE" in text
    assert "PER-STRATEGY" in text
    assert "PER-REGIME" in text
