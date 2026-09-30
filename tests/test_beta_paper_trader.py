"""Tests for beta_brain.paper_trader."""
from dataclasses import dataclass
from beta_brain.paper_trader import PaperTrader, PaperTrade


@dataclass
class FakeRisk:
    position_size_qty: float = 1.0
    stop_loss_price: float = 95.0
    take_profit_price: float = 105.0
    risk_amount_usd: float = 100.0


@dataclass
class FakeVerdict:
    final_decision: str = "APPROVED"
    ts: int = 0
    symbol: str = "BTCUSD"
    mode: str = "scalp"
    debate_winner: str = "BUY"
    risk: FakeRisk = None

    def __post_init__(self):
        if self.risk is None:
            self.risk = FakeRisk()


def _candle(o, h, l, c, ts=0):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ts}


def test_open_trade_creates_position():
    pt = PaperTrader("personal", 10000)
    v = FakeVerdict()
    t = pt.open_trade(v, [_candle(99, 100, 98, 100, 1)])
    assert t is not None
    assert t.direction == "BUY"
    assert t.entry_price == 100


def test_open_trade_rejected_verdict_returns_none():
    pt = PaperTrader("personal", 10000)
    v = FakeVerdict(final_decision="REJECTED")
    t = pt.open_trade(v, [_candle(99, 100, 98, 100, 1)])
    assert t is None


def test_open_trade_no_candles_returns_none():
    pt = PaperTrader("personal", 10000)
    v = FakeVerdict()
    t = pt.open_trade(v, [])
    assert t is None


def test_tp_hit_closes_trade():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    closed = pt.process_candle(_candle(100, 106, 99, 105, 2))
    assert len(closed) == 1
    assert closed[0].status == "CLOSED_TP"


def test_sl_hit_closes_trade():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    closed = pt.process_candle(_candle(100, 101, 94, 94, 2))
    assert len(closed) == 1
    assert closed[0].status == "CLOSED_SL"


def test_sl_checked_before_tp():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    closed = pt.process_candle(_candle(100, 106, 94, 100, 2))
    assert closed[0].status == "CLOSED_SL"


def test_timeout_close():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)], max_hold_bars=2)
    pt.process_candle(_candle(100, 101, 99, 100, 2))
    closed = pt.process_candle(_candle(100, 101, 99, 100, 3))
    assert len(closed) == 1
    assert closed[0].status == "CLOSED_TIMEOUT"


def test_close_all_at_price():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    pt.close_all_at_price(_candle(100, 100, 100, 100, 2))
    assert len(pt.open_trades) == 0
    assert len(pt.closed_trades) == 1
    assert pt.closed_trades[0].status == "CLOSED_EOD"


def test_on_trade_close_callback_fires():
    calls = []
    pt = PaperTrader("personal", 10000, on_trade_close=lambda pnl: calls.append(pnl))
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    pt.process_candle(_candle(100, 106, 99, 105, 2))
    assert len(calls) == 1


def test_can_open_respects_max_positions():
    pt = PaperTrader("personal", 10000)
    assert pt.can_open("scalp", 1) is True
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    assert pt.can_open("scalp", 1) is False


def test_get_stats_basic():
    pt = PaperTrader("personal", 10000)
    pt.open_trade(FakeVerdict(), [_candle(99, 100, 98, 100, 1)])
    pt.process_candle(_candle(100, 106, 99, 105, 2))
    stats = pt.get_stats()
    assert stats["total_trades"] == 1
    assert stats["wins"] == 1
    assert stats["net_pnl"] == 5.0


def test_sell_direction():
    v = FakeVerdict(debate_winner="SELL", risk=FakeRisk(stop_loss_price=105.0, take_profit_price=95.0))
    pt = PaperTrader("personal", 10000)
    t = pt.open_trade(v, [_candle(99, 100, 98, 100, 1)])
    assert t.direction == "SELL"
    closed = pt.process_candle(_candle(100, 101, 94, 95, 2))
    assert closed[0].status == "CLOSED_TP"
