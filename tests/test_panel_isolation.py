"""Failure-isolation contract: a broken data source does not blank the page."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("METRA_TOKEN", "tok")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "NBROOK")
    monkeypatch.setenv("CUS_STOP_ID", "CUS")
    monkeypatch.setenv("NWS_LAT", "42.0")
    monkeypatch.setenv("NWS_LON", "-87.0")
    monkeypatch.setenv("NWS_USER_AGENT", "wd test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    cfg_mod._settings = None
    client_mod._client = None
    client_mod._cache = None


@pytest.mark.asyncio
async def test_metra_failure_does_not_500_or_blank_others():
    """If metra.get_metra raises, /api/dashboard still 200s with
    metra.available=False and other panels populated."""
    async def boom(*_a, **_k):
        raise RuntimeError("metra API down")

    metra_mock = AsyncMock(side_effect=boom)
    weather_mock = AsyncMock(return_value={
        "available": True, "error": None, "hours": [], "current": None
    })
    aqi_mock = AsyncMock(return_value={
        "available": True, "error": None, "value": 42, "category": "Good",
        "level": "good", "alert": False
    })

    with patch("wall_dashboard.web.metra.get_metra", new=metra_mock), \
         patch("wall_dashboard.web.weather.get_weather", new=weather_mock), \
         patch("wall_dashboard.web.aqi.get_aqi", new=aqi_mock), \
         patch("wall_dashboard.web.amtrak.get_amtrak",
               return_value={"available": True, "error": None,
                             "northbound": [], "southbound": []}):
        from wall_dashboard.web import build_app
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["metra"]["available"] is False
    assert "metra API down" in body["metra"]["error"]
    assert body["weather"]["available"] is True
    assert body["aqi"]["available"] is True
    assert body["amtrak"]["available"] is True


@pytest.mark.asyncio
async def test_all_four_failing_returns_200_with_unavailable_envelopes():
    """Even if every source fails, the page renders with four 'unavailable' panels."""
    async def boom_async(*_a, **_k):
        raise RuntimeError("source down")

    def boom_sync(*_a, **_k):
        raise RuntimeError("source down")

    with patch("wall_dashboard.web.metra.get_metra", new=AsyncMock(side_effect=boom_async)), \
         patch("wall_dashboard.web.weather.get_weather", new=AsyncMock(side_effect=boom_async)), \
         patch("wall_dashboard.web.aqi.get_aqi", new=AsyncMock(side_effect=boom_async)), \
         patch("wall_dashboard.web.amtrak.get_amtrak", side_effect=boom_sync):
        from wall_dashboard.web import build_app
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    for key in ["metra", "amtrak", "weather", "aqi"]:
        assert body[key]["available"] is False
        assert "source down" in body[key]["error"]
