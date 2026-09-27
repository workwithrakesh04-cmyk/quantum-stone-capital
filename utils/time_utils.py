"""
Time and session utilities.
Forex sessions, killzones, and time normalization for ICT/SMC frameworks.
"""
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional
import pytz


class Session(str, Enum):
    """Major forex trading sessions (in UTC)."""
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"
    OFF_HOURS = "off_hours"


# All times in UTC
SESSION_TIMES = {
    Session.SYDNEY:   (time(21, 0), time(6, 0)),    # 21:00 - 06:00 UTC
    Session.TOKYO:    (time(0, 0),  time(9, 0)),    # 00:00 - 09:00 UTC
    Session.LONDON:   (time(7, 0),  time(16, 0)),   # 07:00 - 16:00 UTC
    Session.NEW_YORK: (time(12, 0), time(21, 0)),   # 12:00 - 21:00 UTC
}

# ICT Killzones (in UTC; NY local: EST = UTC-5, EDT = UTC-4)
KILLZONES_UTC = {
    "asia_kz":      (time(0, 0),  time(4, 0)),
    "london_kz":    (time(7, 0),  time(10, 0)),
    "ny_am_kz":     (time(12, 30), time(15, 30)),
    "ny_pm_kz":     (time(17, 0), time(20, 0)),
}


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(pytz.UTC)


def to_utc(dt: datetime, from_tz: str = "UTC") -> datetime:
    """Convert a naive or aware datetime to UTC."""
    if dt.tzinfo is None:
        dt = pytz.timezone(from_tz).localize(dt)
    return dt.astimezone(pytz.UTC)


def to_ny(dt: datetime) -> datetime:
    """Convert a datetime to New York time (handles DST)."""
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(pytz.timezone("America/New_York"))


def current_session(dt: Optional[datetime] = None) -> Session:
    """Return the currently active forex session."""
    if dt is None:
        dt = utc_now()
    dt = to_utc(dt)
    t = dt.time()

    for session in (Session.NEW_YORK, Session.LONDON, Session.TOKYO, Session.SYDNEY):
        start, end = SESSION_TIMES[session]
        if start <= end:
            if start <= t < end:
                return session
        else:  # wraps midnight
            if t >= start or t < end:
                return session
    return Session.OFF_HOURS


def in_killzone(killzone_name: str, dt: Optional[datetime] = None) -> bool:
    """Check if a given time falls inside an ICT killzone."""
    if killzone_name not in KILLZONES_UTC:
        raise ValueError(f"Unknown killzone: {killzone_name}")
    if dt is None:
        dt = utc_now()
    dt = to_utc(dt)
    start, end = KILLZONES_UTC[killzone_name]
    return start <= dt.time() < end


def active_killzones(dt: Optional[datetime] = None) -> list:
    """Return list of active killzone names."""
    if dt is None:
        dt = utc_now()
    return [kz for kz in KILLZONES_UTC if in_killzone(kz, dt)]


def is_weekend(dt: Optional[datetime] = None) -> bool:
    """True if Saturday/Sunday in UTC."""
    if dt is None:
        dt = utc_now()
    return to_utc(dt).weekday() >= 5


def bars_since(since: datetime, now: Optional[datetime] = None, timeframe_minutes: int = 5) -> int:
    """Count how many bars of given timeframe have elapsed."""
    if now is None:
        now = utc_now()
    delta = now - since
    return int(delta.total_seconds() // (timeframe_minutes * 60))


def timeframe_to_minutes(tf: str) -> int:
    """Convert '1m','5m','15m','1h','4h','1d' to minutes."""
    tf = tf.lower().strip()
    mapping = {
        "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "2h": 120, "4h": 240,
        "1d": 1440, "1w": 10080,
    }
    if tf not in mapping:
        raise ValueError(f"Unknown timeframe: {tf}")
    return mapping[tf]
