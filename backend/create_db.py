"""
Helper script to initialize PostgreSQL database and all tables for Growth Engine.
Usage:
    python create_db.py
"""
import asyncio
import sys
from urllib.parse import unquote, urlparse

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models.base import Base
import app.models  # Registers all models (auth, leads, social, seo, launch, analytics)


async def main():
    raw_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(raw_url)

    user = unquote(parsed.username) if parsed.username else "postgres"
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    target_db = parsed.path.lstrip("/") or "growthengine"

    print(f"Connecting to PostgreSQL at {host}:{port} as user '{user}'...")
    try:
        sys_conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres",
        )
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"\n[ERROR] Password authentication failed for user '{user}'.")
        print(f"Please check your password in backend/.env: DATABASE_URL=postgresql+asyncpg://{user}:<YOUR_PASSWORD>@{host}:{port}/{target_db}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Could not connect to PostgreSQL: {e}\n")
        sys.exit(1)

    # Check if database exists
    db_exists = await sys_conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", target_db
    )
    if not db_exists:
        print(f"Database '{target_db}' does not exist. Creating it now...")
        await sys_conn.execute(f'CREATE DATABASE "{target_db}"')
        print(f"Database '{target_db}' created successfully.")
    else:
        print(f"Database '{target_db}' already exists.")
    await sys_conn.close()

    # Now create all tables via SQLAlchemy
    print(f"Creating all tables in '{target_db}'...")
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    print("\nSUCCESS! All database tables created successfully:")
    table_names = sorted(Base.metadata.tables.keys())
    for t in table_names:
        print(f"  - {t}")
    print("\nYou can now restart uvicorn and register your owner account!\n")


if __name__ == "__main__":
    asyncio.run(main())
