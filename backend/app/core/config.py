from functools import lru_cache
from typing import Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GlobalReach Growth Engine API"
    environment: str = "local"
    api_prefix: str = "/api/v1"

    # PostgreSQL async connection URL (asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/growthengine"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "changeme-jwt-secret-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # Encryption (Fernet key for OAuth tokens)
    encryption_key: str = ""  # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # Frontend URL
    frontend_url: str = "https://www.getyourclientsb2b.com"
    api_url: str = "http://localhost:8000"

    # Dry run mode (default true — nothing sent until owner flips)
    dry_run: bool = True

    # AI
    anthropic_api_key: str = ""

    # Email
    email_provider: str = "resend"
    resend_api_key: str = ""
    sending_domain: str = ""
    physical_address: str = ""
    unsubscribe_secret: str = "changeme-unsubscribe-secret"

    # Social APIs
    x_client_id: str = ""
    x_client_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_api_version: str = ""
    linkedin_organization_id: str = ""
    linkedin_page_access_token: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    instagram_account_id: str = ""
    instagram_access_token: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Storage (Cloudflare R2 / S3 compatible)
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_key: str = ""
    s3_secret: str = ""

    # GlobalReach dogfooding
    globalreach_api_url: str = ""
    globalreach_api_key: str = ""

    # Signup webhook from main product
    signup_webhook_secret: str = "changeme-webhook-secret"

    # Sentry
    sentry_dsn: str = ""

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any) -> str:
        if isinstance(v, str):
            v = v.strip()
            # If using Neon / Supabase / standard postgres URL, ensure asyncpg dialect is specified
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("frontend_url", mode="before")
    @classmethod
    def clean_frontend_url(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().rstrip("/")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x).strip().rstrip("/") for x in parsed if x]
                except Exception:
                    pass
            return [x.strip().rstrip("/") for x in v.split(",") if x.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(x).strip().rstrip("/") for x in v if x]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings


settings = get_settings()
