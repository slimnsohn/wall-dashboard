"""Composes Metra + Amtrak into the iOS-widget JSON shape.

Shape (matches scriptable/northbrook-trains.js):
    { location, trains: [{ type, time, countdown_min, countdown_str }], updated_at }
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .time_utils import format_clock_time, format_countdown

CHICAGO = ZoneInfo("America/Chicago")
WINDOW_MINUTES = 180  # show trains in next 3 hours


def build_trains_view(
    metra: dict,
    amtrak: dict,
    *,
    now: datetime | None = None,
    location: str = "Northbrook",
    max_count: int = 5,
) -> dict:
    """Merge Metra arrivals and Amtrak schedule into widget-shape JSON."""
    if now is None:
        now = datetime.now(CHICAGO)
    now_min = now.hour * 60 + now.minute

    items: list[dict] = []
    if metra.get("available"):
        for a in metra.get("arrivals", []):
            items.append({
                "type": "Metra",
                "pass_minutes": a["pass_minutes"],
                "time": a["time"],
                "countdown_min": a["countdown_min"],
                "countdown_str": a["countdown_str"],
            })
    if amtrak.get("available"):
        for group in ("northbound", "southbound"):
            for t in amtrak.get(group, []):
                pm = t.get("passMinutes")
                if pm is None:
                    continue
                delta = pm - now_min
                if delta < 0:
                    delta += 1440
                items.append({
                    "type": "Amtrak",
                    "pass_minutes": pm,
                    "time": t.get("time") or format_clock_time(pm),
                    "countdown_min": delta,
                    "countdown_str": t.get("countdown_str") or format_countdown(delta),
                })

    items = [i for i in items if 0 <= i["countdown_min"] <= WINDOW_MINUTES]
    items.sort(key=lambda i: i["countdown_min"])
    trains = [
        {
            "type": i["type"],
            "time": i["time"],
            "countdown_min": i["countdown_min"],
            "countdown_str": i["countdown_str"],
        }
        for i in items[:max_count]
    ]

    return {
        "location": location,
        "trains": trains,
        "updated_at": format_clock_time(now_min),
    }
