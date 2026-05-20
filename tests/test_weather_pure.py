import httpx
import pytest
import respx

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod
from wall_dashboard.weather import (
    bootstrap_nws_url,
    feels_like,
    format_hour_label,
    get_weather,
    get_weather_window,
    match_hour,
)


class TestFeelsLike:
    def test_mild_returns_temp(self):
        assert feels_like(70, 50, 5) == 70

    def test_hot_humid_uses_heat_index(self):
        f = feels_like(90, 70, 5)
        assert 104 <= f <= 110

    def test_cold_windy_uses_wind_chill(self):
        f = feels_like(20, 40, 20)
        assert 2 <= f <= 8

    def test_null_temp(self):
        assert feels_like(None, 50, 5) is None

    def test_hot_no_humidity(self):
        assert feels_like(90, None, 5) == 90

    def test_cold_low_wind(self):
        assert feels_like(20, 40, 2) == 20

    def test_just_below_heat_threshold(self):
        assert feels_like(79, 90, 0) == 79

    def test_just_above_wind_chill_threshold(self):
        assert feels_like(51, 40, 30) == 51


class TestGetWeatherWindow:
    def test_before_flip_today(self):
        w = get_weather_window(8, 17, 19)
        assert w["dayOffset"] == 0
        assert w["hours"] == [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

    def test_late_afternoon_narrows(self):
        w = get_weather_window(16, 17, 19)
        assert w["dayOffset"] == 0
        assert w["hours"] == [17, 18, 19]

    def test_at_flip_hour_tomorrow(self):
        w = get_weather_window(17, 17, 19)
        assert w["dayOffset"] == 1
        assert w["hours"] == [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

    def test_evening_tomorrow(self):
        w = get_weather_window(21, 17, 19)
        assert w["dayOffset"] == 1
        assert w["hours"][0] == 7


class TestFormatHourLabel:
    def test_morning(self):
        assert format_hour_label(9) == "9a"

    def test_afternoon(self):
        assert format_hour_label(13) == "1p"

    def test_noon_midnight(self):
        assert format_hour_label(12) == "12p"
        assert format_hour_label(0) == "12a"


class TestMatchHour:
    def test_finds_matching_key(self):
        hourly = [
            {"hourKey": "2026-05-17-13", "temp": 74},
            {"hourKey": "2026-05-17-14", "temp": 76},
        ]
        assert match_hour(hourly, "2026-05-17-14")["temp"] == 76

    def test_returns_none_when_no_match(self):
        assert match_hour([], "2026-05-17-14") is None


@pytest.fixture(autouse=True)
def reset_state():
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
    monkeypatch.setenv("NWS_FORECAST_HOURLY_URL", "")  # explicit empty - override any .env on disk


@pytest.mark.asyncio
@respx.mock
async def test_bootstrap_nws_url_resolves(env):
    respx.get("https://api.weather.gov/points/42.0,-87.0").mock(
        return_value=httpx.Response(
            200,
            json={"properties": {"forecastHourly": "https://api.weather.gov/forecast/abc"}},
        )
    )
    url = await bootstrap_nws_url()
    assert url == "https://api.weather.gov/forecast/abc"


@pytest.mark.asyncio
async def test_get_weather_returns_unavailable_when_url_missing(env):
    r = await get_weather()
    assert r["available"] is False
    assert "NWS_FORECAST_HOURLY_URL" in r["error"]


@pytest.mark.asyncio
@respx.mock
async def test_get_weather_extracts_hours(env, monkeypatch):
    monkeypatch.setenv("NWS_FORECAST_HOURLY_URL", "https://api.weather.gov/forecast/abc")
    respx.get("https://api.weather.gov/forecast/abc").mock(
        return_value=httpx.Response(
            200,
            json={"properties": {"periods": [
                {"startTime": "2026-05-19T13:00:00-05:00", "temperature": 74,
                 "relativeHumidity": {"value": 55}, "windSpeed": "10 mph",
                 "shortForecast": "Sunny"}
            ]}},
        )
    )
    r = await get_weather()
    assert r["available"] is True
    assert r["hours"][0]["temp"] == 74
    assert r["hours"][0]["wind_mph"] == 10
