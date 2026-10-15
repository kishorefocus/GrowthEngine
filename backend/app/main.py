"""
GlobalReach Growth Engine — FastAPI application entry point.
Routes are prefixed under /api/v1.
Public routes: /r/{code}, /webhooks/signup, /healthz
All other routes require JWT authentication.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import check_database_connection, get_db, init_db
from app.core.deps import get_current_user
from app.routers import auth, brand, analytics, webhooks
from app.schemas.auth import UserResponse

# Structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

# Sentry (if DSN configured)
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment=settings.environment,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GlobalReach Growth Engine API (env=%s, dry_run=%s)", settings.environment, settings.dry_run)
    await init_db()
    yield
    logger.info("API shutting down.")


app = FastAPI(
    title="GlobalReach Growth Engine API",
    version="1.0.0",
    description=(
        "Internal admin API for GlobalReach Growth Engine. "
        "Handles cold email outreach, social content automation, video planning, "
        "programmatic SEO, and launch tracking. "
        "DRY_RUN=true by default — all sends are logged until owner enables live mode."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — locked to Vercel domain + local dev
_cors_origins = list(settings.cors_origins)
if settings.frontend_url not in _cors_origins:
    _cors_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health endpoints ────────────────────────────────────────────────────────

@app.get("/healthz", include_in_schema=False)
@app.get("/health", include_in_schema=False)
async def health_check():
    """Railway health endpoint."""
    db_status = await check_database_connection()
    overall = "healthy" if db_status["connected"] else "degraded"
    return {
        "status": overall,
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": settings.dry_run,
        "environment": settings.environment,
        "database": {
            "status": "connected" if db_status["connected"] else "disconnected",
            "latency_ms": db_status["latency_ms"],
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "GlobalReach Growth Engine API",
        "status": "online",
        "documentation": "/docs",
        "health": "/healthz",
        "dry_run": settings.dry_run,
    }


# ─── API v1 routers ──────────────────────────────────────────────────────────

API_PREFIX = settings.api_prefix  # /api/v1

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(brand.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)


# ─── /api/v1/auth/me convenience endpoint ───────────────────────────────────

from app.models.auth import User  # noqa: E402


@app.get(f"{API_PREFIX}/auth/me", response_model=UserResponse, tags=["auth"])
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(id=str(current_user.id), email=current_user.email, role=current_user.role)


# ─── Global exception handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
