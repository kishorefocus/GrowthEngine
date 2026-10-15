import time
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base  # noqa: F401 — keeps Base accessible via database module

# Re-export Base for backwards compat
__all__ = ["Base", "engine", "AsyncSessionLocal", "get_db", "check_database_connection", "init_db"]

# Async PostgreSQL engine with asyncpg
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=settings.environment == "local",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to provide a request-scoped database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> dict:
    """Verifies live PostgreSQL connection via SELECT 1 and records latency."""
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "connected": val == 1,
                "latency_ms": latency_ms,
                "message": "PostgreSQL database connection established successfully.",
                "database_engine": engine.name,
            }
    except Exception as exc:
        return {
            "connected": False,
            "latency_ms": None,
            "message": f"Could not connect to database: {str(exc)}",
            "database_engine": engine.name,
        }


async def init_db() -> None:
    """Create database tables if they do not exist (dev only — use Alembic in production)."""
    # Import all models to register them with Base.metadata
    import app.models  # noqa: F401
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        print(f"[Database Init Warning] Could not auto-create tables: {exc}")
