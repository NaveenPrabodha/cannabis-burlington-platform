from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    s3_bucket: str = Field(default="")
    s3_region: str = Field(default="ca-central-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")

    playwright_headless: bool = Field(default=True)
    scrape_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    )

    log_level: str = Field(default="INFO")
    data_dir: str = Field(default="./data")

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
