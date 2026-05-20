"""Amtrak GTFS weekly schedule + Northbrook pass-time computation."""
from __future__ import annotations

import csv
import io
import logging
import pickle
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .client import get_http_client
from .time_utils import (
    format_clock_time,
    format_countdown,
    gtfs_time_to_minutes,
    minutes_to_hhmm,
    parse_hhmm,
)

logger = logging.getLogger(__name__)

AMTRAK_GTFS_URL = "https://content.amtrak.com/content/gtfs/GTFS.zip"
GLENVIEW_STOP_ID = "GLN"  # Amtrak stop_id for Glenview, IL
CHICAGO = ZoneInfo("America/Chicago")

_SB_HEADSIGN_KEYWORDS = ("chicago",)

# Amtrak routes that stop at Glenview, IL. Filter by route_long_name to exclude
# unrelated trips that happen to share the Glenview stop_id in other GTFS contexts.
WANTED_ROUTE_NAMES = ("Hiawatha Service", "Empire Builder")


def parse_days(bitstring: str) -> list[int]:
    """7-char Mon..Sun bitstring -> sorted day indices (0=Sun..6=Sat).
    Position i (0=Mon) maps to (i+1) % 7."""
    out = []
    for i, ch in enumerate(bitstring[:7]):
        if ch == "1":
            out.append((i + 1) % 7)
    return sorted(out)


def northbrook_minutes(glenview_hhmm: str, direction: str) -> int:
    """Glenview 'HH:MM' + 'NB'/'SB' -> minutes since midnight at Northbrook pass."""
    base = parse_hhmm(glenview_hhmm)
    offset = 3 if direction.strip().upper() == "NB" else -3
    return (base + offset) % 1440


def parse_csv(text: str) -> list[dict]:
    """CSV text -> list of header-keyed dicts. Tolerates CRLF; quoted commas; trims overflow."""
    if not text or not text.strip():
        return []
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return []
    rows = []
    for row in reader:
        if not row:
            continue
        rows.append({h: (row[i] if i < len(row) else "") for i, h in enumerate(header)})
    return rows


def headsign_direction(headsign: str) -> str:
    """Best-effort direction. Default NB for unknowns (north-of-Chicago bias)."""
    h = (headsign or "").lower()
    if any(k in h for k in _SB_HEADSIGN_KEYWORDS):
        return "SB"
    return "NB"


def calendar_bitstring(row: dict) -> str:
    """GTFS calendar row -> 'MTWTFSS' bitstring."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return "".join("1" if str(row.get(d, "0")).strip() == "1" else "0" for d in days)


def union_bits(a: str, b: str) -> str:
    return "".join("1" if x == "1" or y == "1" else "0" for x, y in zip(a, b))


def date_in_window(date_yyyymmdd: str, start: str, end: str) -> bool:
    return start <= date_yyyymmdd <= end


def extract_amtrak_rows(
    gtfs: dict[str, list[dict]],
    today_yyyymmdd: str,
    glenview_stop_id: str,
) -> list[dict]:
    """GTFS dict -> [{trainNum, direction, glenviewTime, days}] for trains
    serving Glenview on today's date. Unions service_ids per (train, direction)."""
    wanted_route_ids = {
        r["route_id"]
        for r in gtfs.get("routes", [])
        if r.get("route_long_name", "").strip() in WANTED_ROUTE_NAMES
    }
    calendar_by_service = {
        r["service_id"]: r
        for r in gtfs.get("calendar", [])
        if date_in_window(today_yyyymmdd, r["start_date"], r["end_date"])
    }
    trips_by_id = {
        t["trip_id"]: t
        for t in gtfs.get("trips", [])
        if t["service_id"] in calendar_by_service
        and t.get("route_id") in wanted_route_ids
    }
    glen_stops = [
        s for s in gtfs.get("stopTimes", [])
        if s["stop_id"] == glenview_stop_id and s["trip_id"] in trips_by_id
    ]

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for st in glen_stops:
        trip = trips_by_id[st["trip_id"]]
        train_num = trip.get("trip_short_name", "")
        direction = headsign_direction(trip.get("trip_headsign", ""))
        cal = calendar_by_service[trip["service_id"]]
        days = calendar_bitstring(cal)
        # Normalize via gtfs_time_to_minutes -> minutes_to_hhmm so the stored value
        # is always zero-padded "HH:MM" regardless of GTFS source formatting.
        time_hhmm = minutes_to_hhmm(gtfs_time_to_minutes(st["departure_time"]))
        key = (train_num, direction)
        if key in by_key:
            by_key[key]["days"] = union_bits(by_key[key]["days"], days)
        else:
            by_key[key] = {
                "trainNum": train_num,
                "direction": direction,
                "glenviewTime": time_hhmm,
                "days": days,
            }

    rows = list(by_key.values())
    rows.sort(key=lambda r: parse_hhmm(r["glenviewTime"]))
    return rows


def compute_amtrak_trains(rows: list[dict], day_index: int) -> list[dict]:
    """Schedule rows + day (0=Sun..6=Sat) -> [{type:'Amtrak', passMinutes}] running today."""
    out = []
    for r in rows:
        if day_index in parse_days(r["days"]):
            out.append({
                "type": "Amtrak",
                "passMinutes": northbrook_minutes(r["glenviewTime"], r["direction"]),
            })
    return out


async def download_and_extract_amtrak_gtfs() -> dict[str, list[dict]]:
    """Download Amtrak GTFS zip and parse the four files we need."""
    client = get_http_client()
    r = await client.get(AMTRAK_GTFS_URL, timeout=60.0)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    out = {}
    for name, key in [
        ("routes.txt", "routes"),
        ("calendar.txt", "calendar"),
        ("trips.txt", "trips"),
        ("stop_times.txt", "stopTimes"),
    ]:
        with z.open(name) as f:
            out[key] = parse_csv(f.read().decode("utf-8"))
    return out


async def refresh_amtrak_schedule(data_dir: Path) -> dict:
    """Download, extract, pickle schedule. Returns {available, error, row_count}."""
    try:
        gtfs = await download_and_extract_amtrak_gtfs()
        today = datetime.now(CHICAGO).strftime("%Y%m%d")
        rows = extract_amtrak_rows(gtfs, today, GLENVIEW_STOP_ID)
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(data_dir / "amtrak_schedule.pkl", "wb") as f:
            pickle.dump({"rows": rows, "refreshed_at": datetime.now().isoformat()}, f)
        logger.info("Refreshed Amtrak schedule: %d rows", len(rows))
        return {"available": True, "error": None, "row_count": len(rows)}
    except Exception as exc:
        logger.exception("refresh_amtrak_schedule failed")
        return {"available": False, "error": str(exc), "row_count": 0}


def load_amtrak_schedule(data_dir: Path) -> list[dict]:
    """Load pickled rows; returns [] if file missing."""
    path = data_dir / "amtrak_schedule.pkl"
    if not path.exists():
        return []
    with open(path, "rb") as f:
        return pickle.load(f).get("rows", [])


def _enrich_trains(rows: list[dict], day_index: int, now_min: int) -> list[dict]:
    """Per-row enrichment: pass-minutes + clock time + countdown."""
    out = []
    for r in rows:
        if day_index not in parse_days(r["days"]):
            continue
        pm = northbrook_minutes(r["glenviewTime"], r["direction"])
        delta = pm - now_min
        if delta < 0:
            delta += 1440
        out.append({
            "type": "Amtrak",
            "trainNum": r["trainNum"],
            "direction": r["direction"],
            "passMinutes": pm,
            "time": format_clock_time(pm),
            "countdown_min": delta,
            "countdown_str": format_countdown(delta),
        })
    return out


def get_amtrak(data_dir: Path) -> dict:
    """Returns: {available, error, northbound: [...], southbound: [...]} for today."""
    try:
        rows = load_amtrak_schedule(data_dir)
        if not rows:
            return {
                "available": False,
                "error": "No Amtrak schedule cached - run scheduler refresh",
                "northbound": [],
                "southbound": [],
            }
        now = datetime.now(CHICAGO)
        # Python weekday(): Mon=0..Sun=6 -> our convention: Sun=0..Sat=6
        day_index = (now.weekday() + 1) % 7
        now_min = now.hour * 60 + now.minute
        all_trains = _enrich_trains(rows, day_index, now_min)
        # Filter to next 6 hours
        upcoming = [t for t in all_trains if t["countdown_min"] <= 360]
        upcoming.sort(key=lambda t: t["countdown_min"])
        nb = [t for t in upcoming if t["direction"] == "NB"]
        sb = [t for t in upcoming if t["direction"] == "SB"]
        return {"available": True, "error": None, "northbound": nb, "southbound": sb}
    except Exception as exc:
        logger.exception("amtrak.get_amtrak failed")
        return {
            "available": False, "error": str(exc),
            "northbound": [], "southbound": [],
        }
