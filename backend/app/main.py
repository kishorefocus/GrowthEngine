from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import check_database_connection, get_db, init_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Attempt to initialize database tables on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="GrowthEngine Backend - FastAPI connected with PostgreSQL",
    lifespan=lifespan,
)

# Configure CORS for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "status": "online",
        "documentation": "/docs",
        "health_endpoint": "/health",
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Returns the live status of the API and its PostgreSQL database connection."""
    db_status = await check_database_connection()
    overall_status = "healthy" if db_status["connected"] else "degraded"

    return {
        "status": overall_status,
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend": {
            "status": "online",
            "framework": "FastAPI",
            "environment": settings.environment,
        },
        "database": {
            "status": "connected" if db_status["connected"] else "disconnected",
            "engine": db_status["database_engine"],
            "latency_ms": db_status["latency_ms"],
            "message": db_status["message"],
        },
    }


@app.get("/api/items", response_model=list[ItemResponse])
async def list_items(db: AsyncSession = Depends(get_db)):
    """Fetch items from PostgreSQL to verify database read operations."""
    try:
        result = await db.execute(select(Item).order_by(Item.id.desc()).limit(20))
        return result.scalars().all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query failed: {str(exc)}",
        )


@app.post("/api/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, db: AsyncSession = Depends(get_db)):
    """Create a sample item in PostgreSQL to verify database write operations."""
    try:
        new_item = Item(title=payload.title, description=payload.description)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return new_item
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database insert failed: {str(exc)}",
        )
