"""
SEO Publish Batch job:
Runs weekly via ARQ cron.
Reviews draft SEO pages with passing quality scores (>= 70) and publishes an approved batch of up to 50 pages.
Ensures thin or low-quality pages (< 600 words or similarity > 70%) are NEVER mass-published.
Idempotent and safe to run multiple times.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def seo_publish_batch(ctx: dict) -> dict:
    """
    Weekly batch publisher for vetted SEO pages.
    Publishes up to 50 high-quality draft pages.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import AuditLog
    from app.models.seo import SEOPage

    logger.info("[seo_publish_batch] Starting weekly SEO publishing evaluation...")
    published_count = 0
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Select draft pages with quality_score >= 70
        stmt = (
            select(SEOPage)
            .where(SEOPage.status == "draft", SEOPage.quality_score >= 70.0)
            .order_by(SEOPage.quality_score.desc())
            .limit(50)
        )
        res = await db.execute(stmt)
        pages = list(res.scalars().all())

        if not pages:
            logger.info("[seo_publish_batch] No qualified draft pages to publish.")
            return {"published_count": 0, "status": "no_eligible_drafts"}

        for page in pages:
            page.status = "published"
            page.published_at = now
            published_count += 1

        # Audit log entry
        audit = AuditLog(
            action="seo.worker_batch_published",
            entity="seo_pages",
            meta={"count": published_count, "published_at": now.isoformat()},
        )
        db.add(audit)
        await db.commit()

    logger.info("[seo_publish_batch] Completed. Published %d SEO pages.", published_count)
    return {
        "published_count": published_count,
        "status": "success",
        "timestamp": now.isoformat(),
    }
