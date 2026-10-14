from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    database_url: str

    cors_origins: list[str] = ["http://localhost:37173"]

    app_timezone: str = "Asia/Tokyo"

    vapid_private_key: SecretStr = Field(min_length=1)
    vapid_subject: str = Field(pattern=r"^(mailto:.+|https://.+)")

    frontend_dist_dir: Path | None = None

    celery_broker_url: str = "redis://localhost:6379/0"

    @field_validator("app_timezone")
    @classmethod
    def _validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (KeyError, ValueError) as e:
            raise ValueError(f"不明なタイムゾーンです: {v}") from e
        return v


settings = Settings()  # type: ignore[call-arg]
