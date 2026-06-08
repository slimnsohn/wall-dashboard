"""Sunrise/sunset times from Open-Meteo's forecast endpoint.

Used to gate the UV display: UV is visible during daylight only, so the
cutoff shifts with the season automatically (later in summer, earlier in
winter).
"""
from __future__ import annotations

import logging

from .client import get_cache, get_http_client
from .config import get_settings

logger = logging.getLogger(__name__)


async def get_astro() -> dict:
    """Returns {available, error, sunsets_iso: [today, tomorrow]}. Never raises.

    sunsets_iso entries are local ISO timestamps in America/Chicago. Tomorrow
    is included so TOMORROW view-mode (post weather_flip_hour) can apply the
    correct day's cutoff to its hourly cells.
    """
    s = get_settings()
    try:
        async def fetch():
            client = get_http_client()
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": s.nws_lat,
                    "longitude": s.nws_lon,
                    "daily": "sunset",
                    "timezone": "America/Chicago",
                    "forecast_days": 2,
                },
            )
            r.raise_for_status()
            return r.json()

        # 6h TTL: sunset doesn't change within a day; one refresh per quarter
        # of the day is plenty.
        data = await get_cache().get_or_fetch("astro", 21600, fetch)
        daily = data.get("daily") or {}
        sunsets = (daily.get("sunset") or [])[:2]
        return {"available": True, "error": None, "sunsets_iso": sunsets}
    except Exception as exc:
        logger.exception("astro.get_astro failed")
        return {"available": False, "error": str(exc), "sunsets_iso": []}
