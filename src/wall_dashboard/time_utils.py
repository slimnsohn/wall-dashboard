from __future__ import annotations

import re

_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")
_GTFS = re.compile(r"^(\d{1,3}):(\d{2}):(\d{2})$")


def parse_hhmm(s: str) -> int:
    """'HH:MM' -> minutes since midnight."""
    m = _HHMM.match(s.strip())
    if not m:
        raise ValueError(f"Bad time: {s!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def minutes_to_hhmm(minutes: int) -> str:
    """Minutes since midnight -> 'HH:MM' (zero-padded)."""
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def gtfs_time_to_minutes(s: str) -> int:
    """GTFS 'HH:MM:SS' (hours may exceed 24 for next-day stops) -> minutes mod 24h."""
    m = _GTFS.match(s.strip())
    if not m:
        raise ValueError(f"Bad GTFS time: {s!r}")
    h = int(m.group(1)) % 24
    return h * 60 + int(m.group(2))


def format_countdown(minutes: int) -> str:
    """Minutes -> '9 min' under an hour, '1h 9m' at/over an hour."""
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60}h {minutes % 60}m"


def format_clock_time(minutes: int) -> str:
    """Minutes since midnight -> '6:43 AM'. Wraps mod 1440."""
    t = minutes % 1440
    h, m = divmod(t, 60)
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {period}"
