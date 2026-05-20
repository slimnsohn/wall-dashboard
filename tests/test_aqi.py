import httpx
import pytest
import respx

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod
from wall_dashboard.aqi import aqi_info, get_aqi


@pytest.fixture(autouse=True)
def reset():
    client_mod._client = None
    client_mod._cache = None
    cfg_mod._settings = None
    yield
    client_mod._client = None
    client_mod._cache = None
    cfg_mod._settings = None


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("METRA_TOKEN", "t")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "n")
    monkeypatch.setenv("CUS_STOP_ID", "c")
    monkeypatch.setenv("NWS_LAT", "42.0")
    monkeypatch.setenv("NWS_LON", "-87.0")
    monkeypatch.setenv("NWS_USER_AGENT", "wd test@example.com")


class TestAqiInfo:
    def test_good_no_alert(self):
        r = aqi_info(42)
        assert r["category"] == "Good"
        assert r["level"] == "good"
        assert r["alert"] is False

    def test_moderate_alerts(self):
        r = aqi_info(86)
        assert r["category"] == "Moderate"
        assert r["alert"] is True

    def test_unhealthy_for_sensitive(self):
        r = aqi_info(130)
        assert r["category"] == "Unhealthy for Sensitive"
        assert r["alert"] is True

    def test_unhealthy(self):
        r = aqi_info(175)
        assert r["category"] == "Unhealthy"
        assert r["alert"] is True

    def test_boundaries(self):
        assert aqi_info(50)["alert"] is False
        assert aqi_info(51)["alert"] is True

    def test_hazardous(self):
        assert aqi_info(420)["category"] == "Hazardous"


@pytest.mark.asyncio
@respx.mock
async def test_get_aqi_returns_envelope(env):
    respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json={"current": {"us_aqi": 42}})
    )
    r = await get_aqi()
    assert r["available"] is True
    assert r["value"] == 42
    assert r["category"] == "Good"


@pytest.mark.asyncio
@respx.mock
async def test_get_aqi_handles_missing_us_aqi(env):
    respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json={"current": {}})
    )
    r = await get_aqi()
    assert r["available"] is False
