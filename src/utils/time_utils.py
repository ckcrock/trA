"""
Time utilities for Indian market trading.
Handles IST timezone, market session detection, and trading day checks.
Reference: MISSING_REQUIREMENTS §5.1
"""

import logging
import os
from datetime import datetime, time, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
import yaml

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# ─── Market Session Boundaries (IST) ─────────────────────────────────
PRE_OPEN_START = time(9, 0)
PRE_OPEN_END = time(9, 15)
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
POST_MARKET_START = time(15, 30)
POST_MARKET_END = time(16, 0)
MIS_SQUARE_OFF = time(15, 15)

# Built-in fallback holidays (partial).
_DEFAULT_NSE_HOLIDAYS = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 2, 26),   # Maha Shivaratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr
    date(2025, 4, 10),   # Shri Ram Navami
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Mahatma Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Prakash Gurpurb
    date(2025, 12, 25),  # Christmas
    date(2026, 1, 26),   # Republic Day
}


def _load_configured_holidays(path: str = "config/market_holidays.yaml") -> set[date]:
    """
    Load trading holidays from config. Expected schema:

    nse:
      - "2026-01-26"
      - "2026-03-14"
    """
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        result: set[date] = set()
        for val in data.get("nse", []):
            result.add(date.fromisoformat(str(val)))
        return result
    except Exception as e:
        logger.warning(f"Failed to load market holidays from {path}: {e}")
        return set()


NSE_HOLIDAYS = _DEFAULT_NSE_HOLIDAYS | _load_configured_holidays()


def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def to_ist(dt: datetime) -> datetime:
    """Convert a datetime to IST timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def is_trading_day(d: Optional[date] = None) -> bool:
    """Check if a date is a trading day (not weekend, not holiday)."""
    if d is None:
        d = now_ist().date()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d in NSE_HOLIDAYS:
        return False
    return True


def get_market_session(dt: Optional[datetime] = None) -> str:
    """
    Determine current market session.
    Returns: 'PRE_OPEN', 'REGULAR', 'POST_MARKET', or 'CLOSED'
    """
    if dt is None:
        dt = now_ist()
    else:
        dt = to_ist(dt)

    if not is_trading_day(dt.date()):
        return "CLOSED"

    t = dt.time()

    if PRE_OPEN_START <= t < PRE_OPEN_END:
        return "PRE_OPEN"
    elif MARKET_OPEN <= t < MARKET_CLOSE:
        return "REGULAR"
    elif POST_MARKET_START <= t < POST_MARKET_END:
        return "POST_MARKET"
    else:
        return "CLOSED"


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """Check if market is in regular trading hours."""
    return get_market_session(dt) == "REGULAR"


def should_square_off_mis(dt: Optional[datetime] = None) -> bool:
    """Check if MIS positions should be squared off (after 15:15)."""
    if dt is None:
        dt = now_ist()
    else:
        dt = to_ist(dt)

    if not is_trading_day(dt.date()):
        return False
    return dt.time() >= MIS_SQUARE_OFF


def time_to_market_open() -> Optional[timedelta]:
    """Get timedelta until next market open. None if market is open."""
    now = now_ist()

    if is_market_open(now):
        return None

    # Find next trading day
    target = now.date()
    if now.time() >= MARKET_CLOSE:
        target += timedelta(days=1)

    while not is_trading_day(target):
        target += timedelta(days=1)

    market_open_dt = datetime.combine(target, MARKET_OPEN, tzinfo=IST)
    return market_open_dt - now


def time_to_market_close() -> Optional[timedelta]:
    """Get timedelta until market close. None if market is closed."""
    now = now_ist()

    if not is_market_open(now):
        return None

    close_dt = datetime.combine(now.date(), MARKET_CLOSE, tzinfo=IST)
    return close_dt - now


def get_previous_trading_day(d: Optional[date] = None) -> date:
    """Get the previous trading day (skipping weekends and holidays)."""
    if d is None:
        d = now_ist().date()
    d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def get_next_trading_day(d: Optional[date] = None) -> date:
    """Get the next trading day (skipping weekends and holidays)."""
    if d is None:
        d = now_ist().date()
    d += timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d
