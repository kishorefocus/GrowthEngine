"""
Social worker jobs:
1. publish_due_posts: runs every 1 minute, publishes scheduled posts via official APIs,
   writes failure errors to posts.error, and respects DRY_RUN.
2. generate_weekly_content_batch: runs Sunday 18:00, creates next week's draft posts
   so the owner only reviews and approves.
3. refresh_social_tokens: runs hourly, refreshes OAuth tokens expiring in <24 hours.
"""
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Optional
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.auth import BrandProfile, SocialAccount
from app.models.social import ContentIdea, Post
from app.providers.social import PostPayload, PublishResult, get_social_publisher
from app.routers.analytics import register_short_link
from app.routers.posts import get_all_screenshots_for_content, get_varied_destination_url
from app.services.audit import write_audit_log
from app.services.crypto import decrypt_token, encrypt_token
from app.services.utm import utm_dict

logger = logging.getLogger(__name__)


async def publish_single_post(session: AsyncSession, post: Post) -> PublishResult:
    """
    Publish a single post immediately using its connected platform account.
    Updates post.status, post.published_at, post.external_post_id, post.error, and audit log.
    """
    acc_res = await session.execute(
        select(SocialAccount).where(SocialAccount.platform == post.platform)
    )
    account = acc_res.scalar_one_or_none()

    access_token = ""
    account_id = None
    if account and account.encrypted_access_token:
        try:
            access_token = decrypt_token(account.encrypted_access_token)
            account_id = account.external_id
        except Exception as exc:
            logger.error("Failed to decrypt access token for %s: %s", post.platform, exc)
            if not settings.dry_run:
                err_msg = "OAuth token decryption failed. Please reconnect your account in Connections."
                post.status = "failed"
                post.error = err_msg
                await session.commit()
                return PublishResult(external_post_id="", success=False, error=err_msg)

    publisher = get_social_publisher(post.platform)
    payload = PostPayload(
        platform=post.platform,
        body=post.body or "",
        media_urls=post.media_urls,
        link_url=post.link_url,
        access_token=access_token,
        account_id=account_id,
    )

    pub_result = await publisher.publish(payload)

    if pub_result.success:
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        post.external_post_id = pub_result.external_post_id
        post.error = None
        logger.info("Published post %s to %s (external_id=%s)", post.id, post.platform, pub_result.external_post_id)
    else:
        post.status = "failed"
        post.error = pub_result.error or "Publishing failed"
        logger.warning("Failed to publish post %s to %s: %s", post.id, post.platform, post.error)

    await write_audit_log(
        session,
        action="post.publish_attempt",
        user_id=None,
        entity="posts",
        entity_id=str(post.id),
        meta={
            "platform": post.platform,
            "success": pub_result.success,
            "external_post_id": pub_result.external_post_id,
            "error": pub_result.error,
            "dry_run": settings.dry_run,
        },
    )
    await session.commit()
    return pub_result


async def publish_due_posts(ctx: Optional[dict] = None, db: Optional[AsyncSession] = None) -> dict:
    """
    Cron job: runs periodically.
    Fetches posts where status='scheduled' and scheduled_at <= now().
    Publishes to platform, records errors or success, respects DRY_RUN.
    """
    logger.info("[publish_due_posts] Checking for due posts (dry_run=%s)", settings.dry_run)
    now = datetime.now(timezone.utc)
    published_count = 0
    failed_count = 0

    async def _process_with_session(session: AsyncSession):
        nonlocal published_count, failed_count
        query = (
            select(Post)
            .where(Post.status == "scheduled")
            .where(Post.scheduled_at <= now)
            .order_by(Post.scheduled_at.asc())
            .limit(20)
        )
        result = await session.execute(query)
        due_posts = result.scalars().all()

        for post in due_posts:
            pub_result = await publish_single_post(session, post)
            if pub_result.success:
                published_count += 1
            else:
                failed_count += 1

    if db is not None:
        await _process_with_session(db)
    else:
        async with AsyncSessionLocal() as session:
            await _process_with_session(session)

    return {"published": published_count, "failed": failed_count}


async def generate_weekly_content_batch(ctx: Optional[dict] = None, db: Optional[AsyncSession] = None) -> dict:
    """
    ARQ Cron job: runs Sunday 18:00.
    Generates next week's platform draft posts for owner review.
    """
    logger.info("[generate_weekly_content_batch] Generating upcoming week's drafts...")

    async def _process_with_session(session: AsyncSession):
        # Fetch or generate 5 ideas
        ideas_res = await session.execute(
            select(ContentIdea).where(ContentIdea.status == "draft").limit(5)
        )
        ideas = list(ideas_res.scalars().all())

        if not ideas:
            # Seed standard ideas if queue is empty
            seed_topics = [
                ("how-to", "How to verify 1,000 B2B emails with zero bounce penalties"),
                ("build-in-public", "Our live deliverability dashboard: why we pause campaigns at 5% bounce"),
                ("competitor_alternatives", "Apollo alternative that prioritizes real-time verification"),
                ("industry_lead_lists", "Top 50 high-growth fintech founders in Austin hiring sales teams"),
                ("tips_and_stats", "The 3 cold outreach mistakes killing agency response rates"),
            ]
            for pillar, topic in seed_topics:
                idea = ContentIdea(topic=topic, pillar=pillar, source="ai", status="draft")
                session.add(idea)
                ideas.append(idea)
            await session.commit()

        # Generate drafts for each idea across platforms
        created_count = 0
        base_time = datetime.now(timezone.utc) + timedelta(days=1)  # starting Monday
        base_time = base_time.replace(hour=14, minute=0, second=0, microsecond=0)

        for idx, idea in enumerate(ideas):
            sched_time = base_time + timedelta(days=idx)
            for plat in ["x", "linkedin", "facebook", "instagram"]:
                short_code = uuid.uuid4().hex[:8]
                dest_url = get_varied_destination_url(idea.topic, plat, f"{idea.id}_{idx}")
                utm = utm_dict(source=plat, medium="social", campaign=idea.pillar or "batch", content=str(idea.id))
                register_short_link(short_code, dest_url, utm)
                link_to_use = dest_url if (not settings.api_url or "localhost" in settings.api_url or "127.0.0.1" in settings.api_url) else f"{settings.api_url}/r/{short_code}"

                body = f"{idea.topic}\n\nFull guide and verified workflows: {link_to_use}"
                media_urls = get_all_screenshots_for_content(dest_url)
                post = Post(
                    idea_id=idea.id,
                    platform=plat,
                    body=body,
                    media_urls=media_urls,
                    link_url=link_to_use,
                    utm=utm,
                    status="pending_approval",
                    scheduled_at=sched_time,
                )
                session.add(post)
                created_count += 1

        await session.commit()
        return created_count

    if db is not None:
        count = await _process_with_session(db)
    else:
        async with AsyncSessionLocal() as session:
            count = await _process_with_session(session)

    return {"drafts_created": count}


async def refresh_social_tokens(ctx: Optional[dict] = None, db: Optional[AsyncSession] = None) -> dict:
    """
    ARQ Cron job: runs hourly.
    Refreshes OAuth tokens for connected social accounts expiring within 24 hours.
    """
    logger.info("[refresh_social_tokens] Checking for expiring tokens...")
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=24)
    refreshed_count = 0

    async def _process_with_session(session: AsyncSession):
        nonlocal refreshed_count
        query = (
            select(SocialAccount)
            .where(SocialAccount.status == "active")
            .where(SocialAccount.expires_at <= cutoff)
        )
        res = await session.execute(query)
        expiring_accounts = res.scalars().all()

        for acc in expiring_accounts:
            if not acc.encrypted_refresh_token:
                continue

            try:
                raw_refresh = decrypt_token(acc.encrypted_refresh_token)
                new_access_token = ""
                new_expires_at = now + timedelta(days=60)

                if acc.platform == "x" and settings.x_client_id and settings.x_client_secret:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post(
                            "https://api.twitter.com/2/oauth2/token",
                            data={
                                "refresh_token": raw_refresh,
                                "grant_type": "refresh_token",
                                "client_id": settings.x_client_id,
                            },
                            auth=(settings.x_client_id, settings.x_client_secret),
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            new_access_token = data.get("access_token")
                            expires_in = data.get("expires_in", 7200)
                            new_expires_at = now + timedelta(seconds=expires_in)

                # Update if new token acquired or fallback simulation
                if new_access_token:
                    acc.encrypted_access_token = encrypt_token(new_access_token)
                    acc.expires_at = new_expires_at
                    refreshed_count += 1
                else:
                    # Extend by 30 days if in dry_run / dev
                    if settings.dry_run:
                        acc.expires_at = now + timedelta(days=30)
                        refreshed_count += 1

            except Exception as exc:
                logger.error("Failed to refresh token for account %s (%s): %s", acc.id, acc.platform, exc)

        await session.commit()

    if db is not None:
        await _process_with_session(db)
    else:
        async with AsyncSessionLocal() as session:
            await _process_with_session(session)

    return {"tokens_refreshed": refreshed_count}
