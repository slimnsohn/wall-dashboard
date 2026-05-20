from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_addon_options() -> None:
    """If running as a Home Assistant add-on, hydrate env vars from /data/options.json.

    HA Supervisor writes the user's Configuration-tab values to this file inside
    the container. We mirror them into os.environ so pydantic-settings picks them up
    via its normal env-var loading. setdefault() means a real env var (or .env on
    disk during local dev) wins over an options.json value of the same name.
    """
    p = Path("/data/options.json")
    if not p.exists():
        return
    try:
        opts = json.loads(p.read_text())
    except Exception:
        return
    for k, v in opts.items():
        if v is None or v == "":
            continue
        os.environ.setdefault(k, str(v))


_load_addon_options()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    metra_token: str
    northbrook_stop_id: str
    cus_stop_id: str

    nws_lat: float
    nws_lon: float
    nws_user_agent: str
    nws_forecast_hourly_url: str = ""

    weather_flip_hour: int = 17
    weather_end_hour: int = 21

    def redacted_metra_token(self) -> str:
        t = self.metra_token
        if len(t) <= 8:
            return "***"
        return f"{t[:4]}***{t[-4:]}"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
