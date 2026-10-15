"""
Analytics rollup job: aggregates link_clicks and signup_attributions
into summary stats. Runs nightly via ARQ cron.

This is an idempotent job — safe to re-run multiple times.
"""
import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def sync_analytics_rollup(ctx: dict) -> dict:
    """
    Nightly analytics rollup job.
    Currently logs a summary — Prompt 4 will store rollup in a dedicated table.

    Returns dict with job result for ARQ keep_result.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import LinkClick, SignupAttribution
    from sqlalchemy import func, select

    logger.info("[sync_analytics_rollup] Starting nightly rollup at %s", datetime.now(timezone.utc).isoformat())

    async with AsyncSessionLocal() as db:
        yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

        # Yesterday's clicks
        clicks = await db.execute(
            select(func.count()).select_from(LinkClick).where(LinkClick.landed_at >= yesterday)
        )
        click_count = clicks.scalar() or 0

        # Yesterday's signups
        signups = await db.execute(
            select(func.count()).select_from(SignupAttribution).where(SignupAttribution.signed_up_at >= yesterday)
        )
        signup_count = signups.scalar() or 0

        # Channel breakdown for yesterday
        channel_breakdown = await db.execute(
            select(LinkClick.utm_source, func.count().label("visits"))
            .where(LinkClick.landed_at >= yesterday)
            .group_by(LinkClick.utm_source)
        )
        channels = {row.utm_source or "direct": row.visits for row in channel_breakdown}

    result = {
        "date": str(yesterday.date()),
        "clicks": click_count,
        "signups": signup_count,
        "channels": channels,
        "conversion_rate_pct": round((signup_count / click_count * 100), 2) if click_count > 0 else 0.0,
    }

    logger.info("[sync_analytics_rollup] Complete: %s", result)
    return result
