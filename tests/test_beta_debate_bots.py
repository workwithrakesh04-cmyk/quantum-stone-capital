"""Tests for beta_brain.debate buy/sell/hold bots + argument scorer."""
from beta_brain.signal import Signal
from beta_brain.debate.buy_bot import BuyBot
from beta_brain.debate.sell_bot import SellBot
from beta_brain.debate.hold_bot import HoldBot
from beta_brain.debate.argument_scorer import ArgumentScorer


def _long(conf=0.7, weight=0.6, name="s1"):
    return Signal(strategy=name, direction="LONG", confidence=conf, weight=weight)


def _short(conf=0.7, weight=0.6, name="s1"):
    return Signal(strategy=name, direction="SHORT", confidence=conf, weight=weight)


# Neutral context: no momentum bonus
CTX_NEUTRAL = {"momentum": 0.0, "volatility": 0.5}
# Bullish context: positive momentum bonus for BUY bot
CTX_BULLISH = {"momentum": 0.5, "volatility": 0.4}


def test_buy_bot_no_signals():
    b = BuyBot()
    a = b.argue([], CTX_NEUTRAL)
    assert a.confidence == 0.0
    assert "No LONG" in a.statement


def test_buy_bot_with_long_signals():
    b = BuyBot()
    a = b.argue([_long(0.7), _long(0.6, name="s2")], CTX_NEUTRAL)
    assert a.confidence > 0.0
    assert a.bot == "BUY"


def test_buy_bot_counter_sell_reduces_confidence():
    b = BuyBot()
    a_no_counter = b.argue([_long(0.7)], CTX_NEUTRAL)
    b2 = BuyBot()
    a_with_counter = b2.argue([_long(0.7), _short(0.7)], CTX_NEUTRAL)
    assert a_with_counter.confidence < a_no_counter.confidence


def test_buy_bot_momentum_bonus_increases_confidence():
    b1 = BuyBot()
    a_neutral = b1.argue([_long(0.5)], CTX_NEUTRAL)
    b2 = BuyBot()
    a_bullish = b2.argue([_long(0.5)], CTX_BULLISH)
    assert a_bullish.confidence >= a_neutral.confidence


def test_sell_bot_no_signals():
    s = SellBot()
    a = s.argue([], CTX_NEUTRAL)
    assert a.confidence == 0.0


def test_sell_bot_with_short_signals():
    s = SellBot()
    a = s.argue([_short(0.7)], CTX_NEUTRAL)
    assert a.confidence > 0.0
    assert a.bot == "SELL"


def test_hold_bot_no_actionable():
    h = HoldBot()
    a = h.argue([], CTX_NEUTRAL)
    assert a.confidence >= 0.15


def test_hold_bot_conflict_increases_confidence():
    h1 = HoldBot()
    a_no_conflict = h1.argue([_long(0.5)], CTX_NEUTRAL)
    h2 = HoldBot()
    a_conflict = h2.argue([_long(0.5), _short(0.5)], CTX_NEUTRAL)
    assert a_conflict.confidence > a_no_conflict.confidence


def test_argument_scorer_evidence_bonus():
    b = BuyBot()
    a1 = b.argue([_long(0.5)], CTX_NEUTRAL)
    a2 = b.argue([_long(0.5, name=f"s{i}") for i in range(10)], CTX_NEUTRAL)
    scorer = ArgumentScorer()
    assert scorer.score(a2) > scorer.score(a1)


def test_argument_scorer_rank_and_best():
    b = BuyBot()
    s = SellBot()
    a_buy = b.argue([_long(0.9)], CTX_NEUTRAL)
    a_sell = s.argue([_short(0.3)], CTX_NEUTRAL)
    scorer = ArgumentScorer()
    ranked = scorer.rank([a_buy, a_sell])
    assert ranked[0] is a_buy
    assert scorer.best([a_buy, a_sell]) is a_buy


def test_argument_scorer_empty_raises():
    import pytest
    scorer = ArgumentScorer()
    with pytest.raises(ValueError):
        scorer.best([])
