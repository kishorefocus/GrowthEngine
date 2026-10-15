from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GrowthEngine API"
    environment: str = "local"
    api_prefix: str = "/api"

    # PostgreSQL async connection URL (asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/growthengine"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
