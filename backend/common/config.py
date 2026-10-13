from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    cors_origins: list[str] = ["http://localhost:37173"]

    s3_bucket: str = "app-local"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"

    llm_model: str = "claude-opus-5"
    llm_max_tokens: int = 16000

    celery_broker_url: str = "redis://localhost:6379/0"


settings = Settings()  # type: ignore[call-arg]
