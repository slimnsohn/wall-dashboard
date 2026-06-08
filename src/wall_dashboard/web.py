"""FastAPI routes for the wall dashboard."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import amtrak, aqi, astro, metra, uv, weather
from .client import close_http_client
from .config import get_settings
from .scheduler import scheduler_lifespan
from .trains_view import build_trains_view

logger = logging.getLogger(__name__)
CHICAGO = ZoneInfo("America/Chicago")


def _data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "data"))


def build_app() -> FastAPI:
    pkg_root = Path(__file__).parent
    templates = Jinja2Templates(directory=str(pkg_root / "templates"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with scheduler_lifespan(app, _data_dir()):
            try:
                yield
            finally:
                await close_http_client()

    app = FastAPI(title="Wall Dashboard", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(pkg_root / "static")), name="static")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    async def _safe_async(coro, label: str):
        try:
            return await coro
        except Exception as exc:
            logger.exception("data source failed: %s", label)
            return {"available": False, "error": str(exc)}

    def _safe_sync(fn, *args, label: str):
        try:
            return fn(*args)
        except Exception as exc:
            logger.exception("data source failed: %s", label)
            return {"available": False, "error": str(exc)}

    @app.get("/api/dashboard")
    async def api_dashboard():
        s = get_settings()
        m, w, a, u, ast = await asyncio.gather(
            _safe_async(metra.get_metra(s.northbrook_stop_id), "metra"),
            _safe_async(weather.get_weather(), "weather"),
            _safe_async(aqi.get_aqi(), "aqi"),
            _safe_async(uv.get_uv(), "uv"),
            _safe_async(astro.get_astro(), "astro"),
        )
        am = _safe_sync(amtrak.get_amtrak, _data_dir(), label="amtrak")
        now = datetime.now(CHICAGO)
        return {
            "now_iso": now.isoformat(),
            "metra": m,
            "amtrak": am,
            "weather": w,
            "aqi": a,
            "uv": u,
            "astro": ast,
            "weather_flip_hour": s.weather_flip_hour,
            "weather_end_hour": s.weather_end_hour,
        }

    @app.get("/api/trains")
    async def api_trains():
        s = get_settings()
        m = await _safe_async(metra.get_metra(s.northbrook_stop_id), "metra")
        am = _safe_sync(amtrak.get_amtrak, _data_dir(), label="amtrak")
        # Ensure shape compatibility for the merger
        if "arrivals" not in m:
            m["arrivals"] = []
        for key in ("northbound", "southbound"):
            if key not in am:
                am[key] = []
        return build_trains_view(m, am, location="Northbrook")

    @app.get("/api/metra/alerts")
    async def api_metra_alerts():
        try:
            feed = await metra.fetch_alerts()
            return {
                "available": True,
                "alerts": [
                    {
                        "id": e.id,
                        "header": (
                            e.alert.header_text.translation[0].text
                            if e.alert.header_text.translation else ""
                        ),
                    }
                    for e in feed.entity if e.HasField("alert")
                ],
            }
        except Exception as exc:
            return JSONResponse(
                {"available": False, "error": str(exc), "alerts": []}, status_code=200
            )

    @app.get("/api/metra/positions")
    async def api_metra_positions():
        try:
            feed = await metra.fetch_positions()
            return {
                "available": True,
                "positions": [
                    {
                        "trip_id": e.vehicle.trip.trip_id,
                        "lat": e.vehicle.position.latitude,
                        "lon": e.vehicle.position.longitude,
                    }
                    for e in feed.entity if e.HasField("vehicle")
                ],
            }
        except Exception as exc:
            return JSONResponse(
                {"available": False, "error": str(exc), "positions": []}, status_code=200
            )

    @app.get("/")
    async def index(request: Request):
        now = datetime.now(CHICAGO)
        return templates.TemplateResponse(
            request, "dashboard.html", {"now_iso": now.isoformat()}
        )

    @app.get("/trains")
    async def trains_page(request: Request):
        now = datetime.now(CHICAGO)
        return templates.TemplateResponse(
            request, "trains.html", {"now_iso": now.isoformat()}
        )

    return app


app = build_app()
