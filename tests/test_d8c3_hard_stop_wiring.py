"""D8c-3 tests - window_hard_stop_pct wiring through WalkForwardRunner."""
import pytest

from backtest.walk_forward_beta import WalkForwardRunner


class TestConstructor:

    def test_default_is_disabled(self):
        r = WalkForwardRunner(n_windows=2, window_size=500, step_size=250)
        assert r.window_hard_stop_pct == 0.0

    def test_explicit_value_stored(self):
        r = WalkForwardRunner(
            n_windows=2, window_size=500, step_size=250,
            window_hard_stop_pct=3.0,
        )
        assert r.window_hard_stop_pct == 3.0

    def test_coerced_to_float(self):
        r = WalkForwardRunner(
            n_windows=2, window_size=500, step_size=250,
            window_hard_stop_pct=3,   # int, not float
        )
        assert isinstance(r.window_hard_stop_pct, float)
        assert r.window_hard_stop_pct == 3.0


class TestPassThrough:
    """Verify _run_one_window constructs BetaBacktester with the right value.

    We patch BetaBacktester at the module level to capture kwargs without
    running the full pipeline.
    """

    def test_beta_backtester_receives_value(self, monkeypatch):
        captured = {}

        class FakeBT:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.trader = None
                self.max_hold_bars = 0
            def run_on_candles(self, candles):
                from backtest.beta_backtester import BacktestResult
                return BacktestResult(
                    symbol="BTCUSDT", timeframe="5m",
                    start_iso="2026-01-01T00:00:00+00:00",
                    end_iso="2026-01-01T01:00:00+00:00",
                    total_candles=len(candles),
                    warmup=100, runtime_sec=0.0,
                    stats={}, trades=[],
                )
            def get_diagnostics(self):
                return {}

        import backtest.walk_forward_beta as wf
        monkeypatch.setattr(wf, "BetaBacktester", FakeBT)

        r = WalkForwardRunner(
            n_windows=1, window_size=500, step_size=250,
            window_hard_stop_pct=3.0,
        )
        candles = [{"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                    "open_time": 1000 * i} for i in range(600)]
        r._run_one_window(
            window_idx=0,
            candles_slice=candles,
            window_start_idx=0,
            window_end_idx=600,
        )
        assert captured.get("window_hard_stop_pct") == 3.0

    def test_default_disabled_passes_zero(self, monkeypatch):
        captured = {}

        class FakeBT:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.trader = None
                self.max_hold_bars = 0
            def run_on_candles(self, candles):
                from backtest.beta_backtester import BacktestResult
                return BacktestResult(
                    symbol="BTCUSDT", timeframe="5m",
                    start_iso="2026-01-01T00:00:00+00:00",
                    end_iso="2026-01-01T01:00:00+00:00",
                    total_candles=len(candles),
                    warmup=100, runtime_sec=0.0,
                    stats={}, trades=[],
                )
            def get_diagnostics(self):
                return {}

        import backtest.walk_forward_beta as wf
        monkeypatch.setattr(wf, "BetaBacktester", FakeBT)

        r = WalkForwardRunner(n_windows=1, window_size=500, step_size=250)
        candles = [{"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                    "open_time": 1000 * i} for i in range(600)]
        r._run_one_window(
            window_idx=0,
            candles_slice=candles,
            window_start_idx=0,
            window_end_idx=600,
        )
        assert captured.get("window_hard_stop_pct") == 0.0