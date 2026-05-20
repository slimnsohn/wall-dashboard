import pytest
from httpx import ASGITransport, AsyncClient

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("METRA_TOKEN", "tok-abcdef-12345678")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "NBROOK")
    monkeypatch.setenv("CUS_STOP_ID", "CUS")
    monkeypatch.setenv("NWS_LAT", "42.0")
    monkeypatch.setenv("NWS_LON", "-87.0")
    monkeypatch.setenv("NWS_USER_AGENT", "wd test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    cfg_mod._settings = None
    client_mod._client = None
    client_mod._cache = None
    yield
    cfg_mod._settings = None
    client_mod._client = None
    client_mod._cache = None


@pytest.mark.asyncio
async def test_healthz():
    from wall_dashboard.web import build_app
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_dashboard_returns_envelope_keys():
    from wall_dashboard.web import build_app
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {"now_iso", "metra", "amtrak", "weather", "aqi"}
    for key in ["metra", "amtrak", "weather", "aqi"]:
        assert "available" in body[key], f"missing 'available' on {key}: {body[key]}"


@pytest.mark.asyncio
async def test_api_trains_returns_widget_shape():
    from wall_dashboard.web import build_app
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/api/trains")
    assert r.status_code == 200
    body = r.json()
    assert {"location", "trains", "updated_at"} <= set(body.keys())


@pytest.mark.asyncio
async def test_index_serves_html():
    from wall_dashboard.web import build_app
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_trains_page_serves_html():
    from wall_dashboard.web import build_app
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/trains")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
