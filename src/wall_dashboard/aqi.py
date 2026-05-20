"""Open-Meteo current US AQI."""
from __future__ import annotations

import logging

from .client import get_cache, get_http_client
from .config import get_settings

logger = logging.getLogger(__name__)


def aqi_info(value: int) -> dict:
    """US AQI tier per EPA: Good 0-50, Moderate 51-100, Unhealthy-for-Sensitive 101-150,
    Unhealthy 151-200, Very Unhealthy 201-300, Hazardous 301+."""
    if value <= 50:
        return {"category": "Good", "level": "good", "alert": False}
    if value <= 100:
        return {"category": "Moderate", "level": "moderate", "alert": True}
    if value <= 150:
        return {"category": "Unhealthy for Sensitive", "level": "unhealthy", "alert": True}
    if value <= 200:
        return {"category": "Unhealthy", "level": "unhealthy", "alert": True}
    if value <= 300:
        return {"category": "Very Unhealthy", "level": "very-unhealthy", "alert": True}
    return {"category": "Hazardous", "level": "hazardous", "alert": True}


async def get_aqi() -> dict:
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
                    "current": "us_aqi",
                    "timezone": "America/Chicago",
                },
            )
            r.raise_for_status()
            return r.json()

        data = await get_cache().get_or_fetch("aqi", 1800, fetch)
        current = data.get("current") or {}
        val = current.get("us_aqi")
        if val is None:
            return {"available": False, "error": "AQI response missing us_aqi"}
        info = aqi_info(round(val))
        return {"available": True, "error": None, "value": round(val), **info}
    except Exception as exc:
        logger.exception("aqi.get_aqi failed")
        return {"available": False, "error": str(exc)}
