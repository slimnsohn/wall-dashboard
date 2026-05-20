"""Metra origin->destination departure computation with realtime overlay.

Minimal implementation focused on the spec's Layer 3 generalization for the
ad-hoc /api/metra/next endpoint. The live dashboard uses
metra.get_metra_arrivals_for_stop() directly.
"""
from __future__ import annotations

from datetime import datetime


def combine_scheduled_and_realtime(
    scheduled: list[dict],
    realtime_by_trip: dict[str, dict],
) -> list[dict]:
    """For each scheduled trip, overlay realtime prediction if present.

    scheduled: [{trip_id, scheduled_departure_iso, destination_name}]
    realtime_by_trip: {trip_id: {predicted_epoch, canceled?: bool}}
    Returns enriched list with is_live, predicted_departure_iso,
    delay_minutes, status.
    """
    out = []
    for s in scheduled:
        rt = realtime_by_trip.get(s["trip_id"])
        scheduled_dt = datetime.fromisoformat(s["scheduled_departure_iso"])
        if rt and rt.get("canceled"):
            status = "cancelled"
            predicted_iso = None
            delay = None
            is_live = True
        elif rt and rt.get("predicted_epoch"):
            predicted_dt = datetime.fromtimestamp(rt["predicted_epoch"], scheduled_dt.tzinfo)
            delay = int(round((predicted_dt - scheduled_dt).total_seconds() / 60))
            predicted_iso = predicted_dt.isoformat()
            is_live = True
            status = "delayed" if delay > 1 else "on_time"
        else:
            status = "scheduled"
            predicted_iso = None
            delay = None
            is_live = False
        out.append({
            **s,
            "is_live": is_live,
            "predicted_departure_iso": predicted_iso,
            "delay_minutes": delay,
            "status": status,
        })
    return out
