from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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
