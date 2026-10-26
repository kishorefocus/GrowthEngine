"""
GlobalReach Growth Engine — FastAPI application entry point.
Routes are prefixed under /api/v1.
Public routes: /r/{code}, /webhooks/signup, /healthz
All other routes require JWT authentication.
"""
import asyncio
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
from app.routers import (
    analytics,
    auth,
    brand,
    campaigns,
    connections,
    email_events,
    icps,
    ideas,
    launch,
    leads,
    posts,
    reviews,
    seo,
    tools,
    videos,
    webhooks,
)
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


async def _background_scheduler():
    """Periodic scheduler loop for executing due social posts and due emails in environments without an external Redis worker."""
    while True:
        try:
            await asyncio.sleep(30)
            from worker.jobs.social import publish_due_posts
            from worker.jobs.email import send_due_emails
            await publish_due_posts()
            await send_due_emails()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("[background_scheduler] Periodic job error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GlobalReach Growth Engine API (env=%s, dry_run=%s)", settings.environment, settings.dry_run)
    await init_db()
    sched_task = asyncio.create_task(_background_scheduler())
    yield
    sched_task.cancel()
    try:
        await sched_task
    except asyncio.CancelledError:
        pass
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
_cors_origins = [orig.rstrip("/") for orig in settings.cors_origins]
if settings.frontend_url:
    clean_frontend = settings.frontend_url.rstrip("/")
    if clean_frontend not in _cors_origins:
        _cors_origins.append(clean_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"^https://([a-zA-Z0-9-]+\.)*vercel\.app$|^http://(localhost|127\.0\.0\.1)(:\d+)?$",
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
app.include_router(analytics.router)  # public /r/{code} at root
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(icps.router, prefix=API_PREFIX)
app.include_router(campaigns.router, prefix=API_PREFIX)
app.include_router(leads.router, prefix=API_PREFIX)
app.include_router(leads.router)  # public /u/{token}
app.include_router(email_events.router, prefix=API_PREFIX)
app.include_router(email_events.router)  # public /webhooks/email and /webhooks/email/inbound
# Prompt 3 routers
app.include_router(connections.router, prefix=API_PREFIX)
app.include_router(ideas.router, prefix=API_PREFIX)
app.include_router(posts.router, prefix=API_PREFIX)
app.include_router(videos.router, prefix=API_PREFIX)
# Prompt 4 routers
app.include_router(seo.router, prefix=f"{API_PREFIX}/seo")
app.include_router(seo.public_router, prefix=API_PREFIX)
app.include_router(seo.public_router)  # also public at /public/seo
app.include_router(tools.router, prefix=API_PREFIX)
app.include_router(tools.router)  # also public at /public/tools
app.include_router(tools.admin_tools_router, prefix=API_PREFIX)
app.include_router(launch.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)

import os
from fastapi.staticfiles import StaticFiles

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

_screenshots_dir = os.path.join(os.path.dirname(__file__), "static", "screenshots")
if os.path.exists(_screenshots_dir):
    app.mount("/screenshots", StaticFiles(directory=_screenshots_dir), name="screenshots")


# ─── /api/v1/auth/me convenience endpoint ───────────────────────────────────

from app.models.auth import User  # noqa: E402


@app.get(f"{API_PREFIX}/auth/me", response_model=UserResponse, tags=["auth"])
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(id=str(current_user.id), email=current_user.email, role=current_user.role)


# ─── Global exception handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
