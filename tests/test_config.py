from wall_dashboard.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("METRA_TOKEN", "abc")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "NBR")
    monkeypatch.setenv("CUS_STOP_ID", "CUS")
    monkeypatch.setenv("NWS_LAT", "42.1275")
    monkeypatch.setenv("NWS_LON", "-87.8290")
    monkeypatch.setenv("NWS_USER_AGENT", "wall-dashboard test@example.com")
    s = Settings(_env_file=None)
    assert s.metra_token == "abc"
    assert s.northbrook_stop_id == "NBR"
    assert s.nws_lat == 42.1275
    assert s.weather_flip_hour == 17


def test_redacted_token_masks_middle(monkeypatch):
    monkeypatch.setenv("METRA_TOKEN", "359|5xctzrOcL4YtTJ8vtau4xtfax8ps7rVfQ9zyX9id31ba1a00")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "x")
    monkeypatch.setenv("CUS_STOP_ID", "y")
    monkeypatch.setenv("NWS_LAT", "0")
    monkeypatch.setenv("NWS_LON", "0")
    monkeypatch.setenv("NWS_USER_AGENT", "ua")
    s = Settings(_env_file=None)
    r = s.redacted_metra_token()
    assert r.startswith("359|") and r.endswith("1a00") and "***" in r
    assert s.metra_token not in r
