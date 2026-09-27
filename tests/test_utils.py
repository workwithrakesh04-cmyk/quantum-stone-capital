"""Tests for utils (logger, time_utils, math_utils)."""
import math
from datetime import datetime, timedelta
import pytz
import pytest

from utils.time_utils import (
    Session, current_session, in_killzone, active_killzones,
    is_weekend, timeframe_to_minutes, to_utc, to_ny,
)
from utils.math_utils import (
    z_score, rolling_mean, rolling_std, atr, true_range,
    normalize, pct_change, sharpe_ratio, max_drawdown,
)


# ---------- time_utils ----------

def test_timeframe_to_minutes():
    assert timeframe_to_minutes("1m") == 1
    assert timeframe_to_minutes("5m") == 5
    assert timeframe_to_minutes("1h") == 60
    assert timeframe_to_minutes("4h") == 240
    assert timeframe_to_minutes("1d") == 1440


def test_timeframe_to_minutes_invalid():
    with pytest.raises(ValueError):
        timeframe_to_minutes("7m")


def test_session_london():
    # 10:00 UTC is London session
    dt = datetime(2024, 6, 3, 10, 0, tzinfo=pytz.UTC)
    assert current_session(dt) == Session.LONDON


def test_session_ny():
    # 15:00 UTC is NY session
    dt = datetime(2024, 6, 3, 15, 0, tzinfo=pytz.UTC)
    assert current_session(dt) == Session.NEW_YORK


def test_session_tokyo():
    # 03:00 UTC is Tokyo
    dt = datetime(2024, 6, 3, 3, 0, tzinfo=pytz.UTC)
    assert current_session(dt) == Session.TOKYO


def test_killzone_london():
    # 08:00 UTC is inside london_kz (07:00-10:00)
    dt = datetime(2024, 6, 3, 8, 0, tzinfo=pytz.UTC)
    assert in_killzone("london_kz", dt)


def test_killzone_outside():
    dt = datetime(2024, 6, 3, 5, 0, tzinfo=pytz.UTC)
    assert not in_killzone("london_kz", dt)


def test_active_killzones():
    dt = datetime(2024, 6, 3, 8, 0, tzinfo=pytz.UTC)
    kzs = active_killzones(dt)
    assert "london_kz" in kzs


def test_is_weekend():
    sat = datetime(2024, 6, 8, 12, 0, tzinfo=pytz.UTC)  # Saturday
    mon = datetime(2024, 6, 10, 12, 0, tzinfo=pytz.UTC)  # Monday
    assert is_weekend(sat)
    assert not is_weekend(mon)


def test_to_utc_from_ny():
    ny = pytz.timezone("America/New_York")
    dt = ny.localize(datetime(2024, 6, 3, 12, 0))
    utc = to_utc(dt)
    # June = EDT = UTC-4 → 12:00 EDT = 16:00 UTC
    assert utc.hour == 16


# ---------- math_utils ----------

def test_z_score():
    assert z_score(5, 5, 1) == 0.0
    assert z_score(7, 5, 1) == 2.0
    assert z_score(3, 5, 1) == -2.0
    assert z_score(5, 5, 0) == 0.0  # std=0 → 0


def test_rolling_mean():
    assert rolling_mean([1, 2, 3, 4, 5], 3) == 4.0


def test_rolling_std():
    val = rolling_std([2, 4, 4, 4, 5, 5, 7, 9], 8)
    assert abs(val - 2.138) < 0.01


def test_true_range():
    assert true_range(10, 5, 8) == 5      # H-L = 5
    assert true_range(10, 9, 8) == 2      # H-PC = 2


def test_atr_basic():
    highs =  [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
    lows =   [ 5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    closes = [ 7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    val = atr(highs, lows, closes, period=14)
    assert val > 0


def test_normalize():
    assert normalize(5, 0, 10) == 0.5
    assert normalize(0, 0, 10) == 0.0
    assert normalize(10, 0, 10) == 1.0
    assert normalize(5, 5, 5) == 0.5  # degenerate


def test_pct_change():
    assert pct_change(110, 100) == 0.1
    assert pct_change(90, 100) == -0.1
    assert pct_change(100, 0) == 0.0


def test_sharpe_ratio():
    returns = [0.01, 0.02, -0.005, 0.015, 0.01, 0.005]
    sr = sharpe_ratio(returns)
    assert sr > 0


def test_max_drawdown():
    curve = [100, 110, 105, 120, 90, 100]
    dd = max_drawdown(curve)
    # Peak 120 → trough 90 → 25% DD
    assert abs(dd - 0.25) < 0.001
