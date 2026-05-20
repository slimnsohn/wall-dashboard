"""Open-Meteo current + hourly UV index."""
from __future__ import annotations

import logging
from datetime import datetime

from .client import get_cache, get_http_client
from .config import get_settings

logger = logging.getLogger(__name__)


def uv_info(value: float) -> dict:
    """EPA UV index tier: Low (0-2), Moderate (3-5), High (6-7),
    Very High (8-10), Extreme (11+)."""
    v = round(value)
    if v <= 2:
        return {"category": "Low", "level": "low", "alert": False}
    if v <= 5:
        return {"category": "Moderate", "level": "moderate", "alert": True}
    if v <= 7:
        return {"category": "High", "level": "high", "alert": True}
    if v <= 10:
        return {"category": "Very High", "level": "very-high", "alert": True}
    return {"category": "Extreme", "level": "extreme", "alert": True}


def _parse_hourly_uv(payload: dict) -> list[dict]:
    """Open-Meteo hourly arrays -> list of per-hour UV records with hourKey
    matching weather.py's format so the frontend can merge them by key."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get("uv_index") or []
    out: list[dict] = []
    for t, v in zip(times, values):
        if v is None:
            continue
        try:
            dt = datetime.fromisoformat(t)
        except ValueError:
            continue
        info = uv_info(v)
        out.append({
            "hourKey": f"{dt.year}-{dt.month:02d}-{dt.day:02d}-{dt.hour}",
            "hour": dt.hour,
            "value": round(v),
            **info,
        })
    return out


async def get_uv() -> dict:
    """Returns: {available, error, value, category, level, alert, hours: [...]}."""
    s = get_settings()
    try:
        async def fetch():
            client = get_http_client()
            r = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": s.nws_lat,
                    "longitude": s.nws_lon,
                    "current": "uv_index",
                    "hourly": "uv_index",
                    "forecast_days": 3,
                    "timezone": "America/Chicago",
                },
            )
            r.raise_for_status()
            return r.json()

        data = await get_cache().get_or_fetch("uv", 1800, fetch)
        hours = _parse_hourly_uv(data)
        current = data.get("current") or {}
        val = current.get("uv_index")
        if val is None:
            return {
                "available": False,
                "error": "UV response missing uv_index",
                "hours": hours,
            }
        info = uv_info(val)
        return {
            "available": True,
            "error": None,
            "value": round(val, 1),
            "hours": hours,
            **info,
        }
    except Exception as exc:
        logger.exception("uv.get_uv failed")
        return {"available": False, "error": str(exc), "hours": []}
