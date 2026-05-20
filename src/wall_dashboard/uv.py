"""Open-Meteo current UV index."""
from __future__ import annotations

import logging

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


async def get_uv() -> dict:
    """Returns: {available, error, value, category, level, alert}."""
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
                    "timezone": "America/Chicago",
                },
            )
            r.raise_for_status()
            return r.json()

        data = await get_cache().get_or_fetch("uv", 1800, fetch)
        current = data.get("current") or {}
        val = current.get("uv_index")
        if val is None:
            return {"available": False, "error": "UV response missing uv_index"}
        info = uv_info(val)
        return {"available": True, "error": None, "value": round(val, 1), **info}
    except Exception as exc:
        logger.exception("uv.get_uv failed")
        return {"available": False, "error": str(exc)}
