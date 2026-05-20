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
        print("[addon-config] /data/options.json does not exist", flush=True)
        return
    try:
        raw = p.read_text()
        opts = json.loads(raw)
    except Exception as exc:
        print(f"[addon-config] failed to parse options.json: {exc}", flush=True)
        return
    # Log keys + value lengths (don't leak the values themselves)
    summary = {k: (f"len={len(v)}" if isinstance(v, str) else type(v).__name__)
               for k, v in opts.items()}
    print(f"[addon-config] options.json keys: {summary}", flush=True)
    loaded, skipped = [], []
    for k, v in opts.items():
        if v is None or v == "":
            skipped.append(k)
            continue
        os.environ.setdefault(k, str(v))
        loaded.append(k)
    print(f"[addon-config] env set: {sorted(loaded)}", flush=True)
    print(f"[addon-config] skipped (empty): {sorted(skipped)}", flush=True)


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
