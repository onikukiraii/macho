from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    cors_origins: list[str] = ["http://localhost:37173"]

    app_timezone: str = "Asia/Tokyo"

    vapid_private_key: SecretStr
    vapid_subject: str

    frontend_dist_dir: Path | None = None

    celery_broker_url: str = "redis://localhost:6379/0"


settings = Settings()  # type: ignore[call-arg]
