"""Metra GTFS-Realtime client (alerts, positions, tripupdates)."""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from google.transit import gtfs_realtime_pb2

from .client import get_cache, get_http_client
from .config import get_settings
from .time_utils import format_clock_time, format_countdown

logger = logging.getLogger(__name__)

BASE_URL = "https://gtfspublic.metrarr.com/gtfs/public"
TTL_SECONDS = 30
CHICAGO = ZoneInfo("America/Chicago")


def _auth_headers() -> dict[str, str]:
    s = get_settings()
    return {"Authorization": f"Bearer {s.metra_token}"}


async def _fetch_feed(endpoint: str) -> gtfs_realtime_pb2.FeedMessage:
    client = get_http_client()
    r = await client.get(f"{BASE_URL}/{endpoint}", headers=_auth_headers())
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    return feed


async def fetch_tripupdates() -> gtfs_realtime_pb2.FeedMessage:
    async def fetch():
        return await _fetch_feed("tripupdates")
    return await get_cache().get_or_fetch("metra_tripupdates", TTL_SECONDS, fetch)


async def fetch_alerts() -> gtfs_realtime_pb2.FeedMessage:
    async def fetch():
        return await _fetch_feed("alerts")
    return await get_cache().get_or_fetch("metra_alerts", TTL_SECONDS, fetch)


async def fetch_positions() -> gtfs_realtime_pb2.FeedMessage:
    async def fetch():
        return await _fetch_feed("positions")
    return await get_cache().get_or_fetch("metra_positions", TTL_SECONDS, fetch)


async def get_metra_arrivals_for_stop(stop_id: str) -> list[dict]:
    """Returns: [{trip_id, route_id, arrival_epoch}], upcoming arrivals at stop_id."""
    feed = await fetch_tripupdates()
    now = datetime.now(CHICAGO).timestamp()
    out = []
    for e in feed.entity:
        if not e.HasField("trip_update"):
            continue
        tu = e.trip_update
        for stu in tu.stop_time_update:
            if stu.stop_id != stop_id:
                continue
            if stu.HasField("arrival") and stu.arrival.time:
                arrival = stu.arrival.time
            elif stu.HasField("departure") and stu.departure.time:
                arrival = stu.departure.time
            else:
                continue
            # Allow 60s grace for trains "now" - already-passed trains are filtered
            if arrival < now - 60:
                continue
            out.append({
                "trip_id": tu.trip.trip_id,
                "route_id": tu.trip.route_id,
                "arrival_epoch": int(arrival),
            })
    return sorted(out, key=lambda x: x["arrival_epoch"])


async def get_metra(stop_id: str) -> dict:
    """Returns: {available, error, arrivals: [{trip_id, route_id, arrival_epoch,
    pass_minutes, time, countdown_min, countdown_str}]}."""
    try:
        arrivals = await get_metra_arrivals_for_stop(stop_id)
        now = datetime.now(CHICAGO)
        now_min = now.hour * 60 + now.minute
        enriched = []
        for a in arrivals:
            arr_dt = datetime.fromtimestamp(a["arrival_epoch"], CHICAGO)
            arr_min = arr_dt.hour * 60 + arr_dt.minute
            delta = arr_min - now_min
            if delta < 0:
                delta += 1440
            enriched.append({
                **a,
                "pass_minutes": arr_min,
                "time": format_clock_time(arr_min),
                "countdown_min": delta,
                "countdown_str": format_countdown(delta),
            })
        return {"available": True, "error": None, "arrivals": enriched}
    except Exception as exc:
        logger.exception("metra.get_metra failed")
        return {"available": False, "error": str(exc), "arrivals": []}
