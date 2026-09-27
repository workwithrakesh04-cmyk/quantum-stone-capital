"""Tests for LiveRunner."""
import pytest
from brokers.paper_broker import PaperBroker
from core.live_runner import LiveRunner, RunnerConfig
from core.market_context import MarketContext


@pytest.fixture
def broker():
    b = PaperBroker(starting_balance=10000.0, prices={"BTCUSD": 40000.0})
    b.connect()
    return b


@pytest.fixture
def runner(broker):
    config = RunnerConfig(
        symbols=["BTCUSD"],
        timeframe="5m",
        poll_seconds=0.0,
        account_name="personal",
        dry_run=True,
    )
    return LiveRunner(broker, config=config)


def test_runner_init(runner):
    assert runner.broker is not None
    assert runner.brain is not None
    assert runner.config.symbols == ["BTCUSD"]


def test_runner_default_context(broker):
    config = RunnerConfig(symbols=["BTCUSD"], dry_run=True)
    runner = LiveRunner(broker, config=config)
    ctx = runner._default_context(broker, "BTCUSD", "5m")
    assert isinstance(ctx, MarketContext)
    assert ctx.symbol == "BTCUSD"
    assert ctx.closes == [40000.0]


def test_runner_tick_once_returns_list(runner):
    results = runner.tick_once()
    assert isinstance(results, list)
    assert len(results) == 1


def test_runner_tick_result_keys(runner):
    results = runner.tick_once()
    r = results[0]
    assert "symbol" in r
    assert "decision" in r
    assert "direction" in r


def test_runner_tick_result_symbol(runner):
    results = runner.tick_once()
    assert results[0]["symbol"] == "BTCUSD"


def test_runner_stop(runner):
    runner.stop()
    assert runner._stop is True


def test_runner_dry_run_no_orders(runner):
    # Force a trade by stubbing brain.run via monkeypatch
    from core.pipeline_result import PipelineResult
    fake = PipelineResult(decision="trade", direction="long", confidence=0.9,
                          position_size=0.01, stop_loss=39000.0, take_profit=41000.0)
    runner.brain.run = lambda *a, **k: fake
    runner.tick_once()
    assert len(broker.open_orders()) == 0  # dry_run=True


def test_runner_live_places_order(broker):
    config = RunnerConfig(symbols=["BTCUSD"], dry_run=False, account_name="personal")
    runner = LiveRunner(broker, config=config)
    from core.pipeline_result import PipelineResult
    fake = PipelineResult(decision="trade", direction="long", confidence=0.9,
                          position_size=0.01, stop_loss=39000.0, take_profit=41000.0)
    runner.brain.run = lambda *a, **k: fake
    runner.tick_once()
    assert len(broker.open_orders()) == 1


def test_runner_multiple_symbols(broker):
    broker.set_price("EURUSD", 1.10)
    config = RunnerConfig(symbols=["BTCUSD", "EURUSD"], dry_run=True)
    runner = LiveRunner(broker, config=config)
    results = runner.tick_once()
    assert len(results) == 2


def test_runner_run_forever_max_iterations(runner):
    # Should return quickly with max_iterations=1 and poll_seconds=0
    runner.config.poll_seconds = 0.0
    runner.run_forever(max_iterations=1)
    # No exception is success
