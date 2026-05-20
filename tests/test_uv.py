import httpx
import pytest
import respx

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod
from wall_dashboard.uv import get_uv, uv_info


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
    monkeypatch.setenv("NWS_USER_AGENT", "wd test")


class TestUvInfo:
    def test_low_no_alert(self):
        r = uv_info(1)
        assert r["category"] == "Low"
        assert r["level"] == "low"
        assert r["alert"] is False

    def test_low_at_boundary_2(self):
        assert uv_info(2)["category"] == "Low"

    def test_moderate(self):
        r = uv_info(4)
        assert r["category"] == "Moderate"
        assert r["alert"] is True

    def test_high(self):
        r = uv_info(7)
        assert r["category"] == "High"
        assert r["level"] == "high"
        assert r["alert"] is True

    def test_very_high(self):
        r = uv_info(9)
        assert r["category"] == "Very High"
        assert r["level"] == "very-high"

    def test_extreme(self):
        r = uv_info(12)
        assert r["category"] == "Extreme"
        assert r["level"] == "extreme"

    def test_zero_is_low(self):
        # UV is 0 at night
        assert uv_info(0)["category"] == "Low"

    def test_float_rounds(self):
        # Open-Meteo returns floats like 6.7
        assert uv_info(6.7)["category"] == "High"  # rounds to 7
        assert uv_info(5.4)["category"] == "Moderate"  # rounds to 5


@pytest.mark.asyncio
@respx.mock
async def test_get_uv_returns_envelope(env):
    respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json={"current": {"uv_index": 6.7}})
    )
    r = await get_uv()
    assert r["available"] is True
    assert r["value"] == 6.7
    assert r["category"] == "High"
    assert r["alert"] is True


@pytest.mark.asyncio
@respx.mock
async def test_get_uv_handles_missing_uv_index(env):
    respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json={"current": {}})
    )
    r = await get_uv()
    assert r["available"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_uv_handles_uv_zero_at_night(env):
    respx.get("https://air-quality-api.open-meteo.com/v1/air-quality").mock(
        return_value=httpx.Response(200, json={"current": {"uv_index": 0}})
    )
    r = await get_uv()
    assert r["available"] is True
    assert r["value"] == 0
    assert r["category"] == "Low"
    assert r["alert"] is False
