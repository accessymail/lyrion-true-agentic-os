"""Centralized runtime configuration for Lyrion Intelligence OS."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="LYRION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lyrion Intelligence OS"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = False

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://localhost/lyrion"

    model_provider: str = "cloud"
    model_environment: str = "cloud_api"

    telemetry_enabled: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable-by-convention settings instance."""
    return Settings()
