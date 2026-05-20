"""NWS hourly forecast adapter + pure transforms."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .client import get_cache, get_http_client
from .config import get_settings

logger = logging.getLogger(__name__)

CHICAGO = ZoneInfo("America/Chicago")


def feels_like(
    temp_f: float | None,
    humidity_pct: float | None,
    wind_mph: float | None,
) -> float | None:
    """Apparent temperature: Rothfusz heat-index (>=80F and humid) or
    wind chill (<=50F and >3mph wind), else raw temperature."""
    if temp_f is None:
        return None
    t = temp_f
    if t >= 80 and humidity_pct is not None:
        h = humidity_pct
        hi = (
            -42.379 + 2.04901523 * t + 10.14333127 * h
            - 0.22475541 * t * h - 0.00683783 * t * t
            - 0.05481717 * h * h + 0.00122874 * t * t * h
            + 0.00085282 * t * h * h - 0.00000199 * t * t * h * h
        )
        return round(hi)
    if t <= 50 and wind_mph is not None and wind_mph > 3:
        w = wind_mph
        wc = 35.74 + 0.6215 * t - 35.75 * (w ** 0.16) + 0.4275 * t * (w ** 0.16)
        return round(wc)
    return t


def get_weather_window(now_hour: int, flip_hour: int, end_hour: int) -> dict:
    """Decide which day's hours to display.

    Before flip_hour -> rest of today (now_hour+1 through end_hour).
    At/after flip_hour -> tomorrow 7am through end_hour.
    """
    if now_hour < flip_hour:
        return {"dayOffset": 0, "hours": list(range(now_hour + 1, end_hour + 1))}
    return {"dayOffset": 1, "hours": list(range(7, end_hour + 1))}


def format_hour_label(hour: int) -> str:
    """0..23 -> '12a', '1a' ... '12p', '1p' ... '11p'."""
    period = "a" if hour < 12 else "p"
    h12 = hour % 12 or 12
    return f"{h12}{period}"


def match_hour(hourly: list[dict], key: str) -> dict | None:
    for h in hourly:
        if h.get("hourKey") == key:
            return h
    return None


async def bootstrap_nws_url() -> str:
    """Resolve the NWS hourly forecast URL for the configured lat/lon.

    Caller writes the result into .env on the Green.
    """
    s = get_settings()
    client = get_http_client()
    r = await client.get(
        f"https://api.weather.gov/points/{s.nws_lat},{s.nws_lon}",
        headers={"User-Agent": s.nws_user_agent},
    )
    r.raise_for_status()
    return r.json()["properties"]["forecastHourly"]


def _parse_wind(s: str) -> float | None:
    """'10 mph' or '5 to 10 mph' -> midpoint float."""
    nums = [int(n) for n in re.findall(r"\d+", s or "")]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _extract_hour(period: dict) -> dict:
    """NWS hour period -> compact dashboard hour record."""
    start = period.get("startTime", "")
    try:
        dt = datetime.fromisoformat(start)
    except ValueError:
        dt = datetime.now(CHICAGO)
    temp = period.get("temperature")
    humidity_obj = period.get("relativeHumidity") or {}
    humidity = humidity_obj.get("value")
    wind_mph = _parse_wind(period.get("windSpeed", ""))
    return {
        "hourKey": f"{dt.year}-{dt.month:02d}-{dt.day:02d}-{dt.hour}",
        "hour": dt.hour,
        "temp": temp,
        "humidity": humidity,
        "wind_mph": wind_mph,
        "feels_like": feels_like(temp, humidity, wind_mph),
        "short": period.get("shortForecast"),
    }


async def get_weather() -> dict:
    """Returns: {available, error, hours: [...], current: {...}}. Never raises."""
    s = get_settings()
    try:
        if not s.nws_forecast_hourly_url:
            return {
                "available": False,
                "error": "NWS_FORECAST_HOURLY_URL not set - run 'wall-dashboard bootstrap-nws'",
                "hours": [],
                "current": None,
            }

        async def fetch():
            client = get_http_client()
            r = await client.get(
                s.nws_forecast_hourly_url,
                headers={"User-Agent": s.nws_user_agent},
            )
            r.raise_for_status()
            return r.json()

        raw = await get_cache().get_or_fetch("nws_weather", 900, fetch)
        periods = raw.get("properties", {}).get("periods", [])
        hours = [_extract_hour(p) for p in periods]
        now = datetime.now(CHICAGO)
        current_key = f"{now.year}-{now.month:02d}-{now.day:02d}-{now.hour}"
        current = match_hour(hours, current_key)
        return {"available": True, "error": None, "hours": hours, "current": current}
    except Exception as exc:
        logger.exception("weather.get_weather failed")
        return {"available": False, "error": str(exc), "hours": [], "current": None}
