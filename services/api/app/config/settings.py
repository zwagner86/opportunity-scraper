from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPPORTUNITY_",
        extra="ignore",
    )

    env: str = "local"
    db_path: str = "./data/opportunity_finder.db"
    config_dir: str = "./configs"
    api_title: str = "Opportunity Finder API"
    api_version: str = "0.1.0"
    log_level: str = "INFO"

    @property
    def db_file(self) -> Path:
        return Path(self.db_path).resolve()

    @property
    def config_path(self) -> Path:
        return Path(self.config_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
