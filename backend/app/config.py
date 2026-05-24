from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="local")
    app_name: str = Field(default="cannabis-backend")
    app_version: str = Field(default="0.1.0")

    database_url: str
    sync_database_url: str

    cors_origins: str = Field(default="http://localhost:3000")
    log_level: str = Field(default="INFO")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
