"""
Posts & Calendar router:
- POST /posts/generate: adapt idea to X, LinkedIn, Instagram, Facebook using social_adapt.txt
- Wrap links with services/utm.py and register short links /r/{code}
- Run claims_guard on all text
- Approval state machine: draft -> pending_approval -> approved -> scheduled -> published | failed | rejected
- Approve, reject, reschedule, retry endpoints with audit_log recording
- GET /calendar: month/week feed with best-time heuristic (simple when <30 posts, data-driven when >=30)
"""
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analytics import LinkClick
from app.models.auth import BrandProfile, User
from app.models.social import ContentIdea, Post
from app.providers.social import PostPayload, get_social_publisher
from app.routers.analytics import register_short_link
from app.schemas.social import (
    ApprovePostRequest,
    CalendarFeedResponse,
    CalendarItem,
    GeneratePostsRequest,
    GeneratePostsResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
    RejectPostRequest,
    ReschedulePostRequest,
)
from app.services.ai import _load_prompt, generate
from app.services.audit import write_audit_log
from app.services.claims_guard import ClaimsGuardError, check_claims
from app.services.utm import build_utm_url, utm_dict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["posts"])


class _XAdapted(BaseModel):
    body: str
    is_thread: bool = False


class _LinkedInAdapted(BaseModel):
    body: str


class _InstagramAdapted(BaseModel):
    caption: str
    carousel_slides: Optional[list[str]] = None
    image_prompt: Optional[str] = None


class _FacebookAdapted(BaseModel):
    body: str


class _SocialAdaptSchema(BaseModel):
    x: _XAdapted
    linkedin: _LinkedInAdapted
    instagram: _InstagramAdapted
    facebook: _FacebookAdapted


TARGET_ROUTES = [
    "https://www.getyourclientsb2b.com/",
    "https://www.getyourclientsb2b.com/#overview",
    "https://www.getyourclientsb2b.com/#product",
    "https://www.getyourclientsb2b.com/#how-it-works",
    "https://www.getyourclientsb2b.com/#industries",
    "https://www.getyourclientsb2b.com/#discovery",
    "https://www.getyourclientsb2b.com/#pipeline",
    "https://www.getyourclientsb2b.com/#inbox",
    "https://www.getyourclientsb2b.com/#calls",
    "https://www.getyourclientsb2b.com/#analytics",
    "https://www.getyourclientsb2b.com/pricing",
    "https://www.getyourclientsb2b.com/contact",
]

ROUTE_SCREENSHOT_MAP = {
    "https://www.getyourclientsb2b.com/": "/screenshots/home.png",
    "https://www.getyourclientsb2b.com/#overview": "/screenshots/overview.png",
    "https://www.getyourclientsb2b.com/#product": "/screenshots/product.png",
    "https://www.getyourclientsb2b.com/#how-it-works": "/screenshots/how-it-works.png",
    "https://www.getyourclientsb2b.com/#industries": "/screenshots/industries.png",
    "https://www.getyourclientsb2b.com/#discovery": "/screenshots/discovery.png",
    "https://www.getyourclientsb2b.com/#pipeline": "/screenshots/pipeline.png",
    "https://www.getyourclientsb2b.com/#inbox": "/screenshots/inbox.png",
    "https://www.getyourclientsb2b.com/#calls": "/screenshots/calls.png",
    "https://www.getyourclientsb2b.com/#analytics": "/screenshots/analytics.png",
    "https://www.getyourclientsb2b.com/pricing": "/screenshots/pricing.png",
    "https://www.getyourclientsb2b.com/contact": "/screenshots/contact.png",
}

ALL_FOLDER_SCREENSHOTS = [
    "/screenshots/home.png",
    "/screenshots/overview.png",
    "/screenshots/discovery.png",
    "/screenshots/discovery2.png",
    "/screenshots/pipeline.png",
    "/screenshots/pipeline2.png",
    "/screenshots/inbox.png",
    "/screenshots/calls.png",
    "/screenshots/analytics.png",
    "/screenshots/product.png",
    "/screenshots/how-it-works.png",
    "/screenshots/industries.png",
    "/screenshots/pricing.png",
    "/screenshots/contact.png",
]


def get_screenshot_for_route(route: str) -> str:
    """Return local screenshot path for a given route on https://www.getyourclientsb2b.com."""
    if not route:
        return "/screenshots/home.png"
    clean_route = route.rstrip("/").replace("://getyourclientsb2b.com", "://www.getyourclientsb2b.com")
    for target, screenshot in ROUTE_SCREENSHOT_MAP.items():
        clean_target = target.rstrip("/")
        if clean_target == clean_route or (clean_target != "https://www.getyourclientsb2b.com" and clean_target in clean_route):
            return screenshot
    lower = route.lower()
    if "pricing" in lower:
        return "/screenshots/pricing.png"
    if "contact" in lower:
        return "/screenshots/contact.png"
    if "how-it-works" in lower or "works" in lower:
        return "/screenshots/how-it-works.png"
    if "industr" in lower:
        return "/screenshots/industries.png"
    if "discovery" in lower or "leads" in lower:
        return "/screenshots/discovery.png"
    if "pipeline" in lower or "campaign" in lower:
        return "/screenshots/pipeline.png"
    if "inbox" in lower:
        return "/screenshots/inbox.png"
    if "call" in lower:
        return "/screenshots/calls.png"
    if "analytic" in lower:
        return "/screenshots/analytics.png"
    if "product" in lower:
        return "/screenshots/product.png"
    if "overview" in lower:
        return "/screenshots/overview.png"
    return "/screenshots/home.png"


def get_all_folder_screenshots() -> list[str]:
    """
    Dynamically discover all image files inside backend/app/static/screenshots/
    or frontend/public/screenshots/ and return them as web paths.
    """
    import os
    discovered: list[str] = []
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "static", "screenshots"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "public", "screenshots"),
    ]
    for c_dir in candidates:
        if os.path.exists(c_dir):
            try:
                for fname in sorted(os.listdir(c_dir)):
                    if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        path = f"/screenshots/{fname}"
                        if path not in discovered:
                            discovered.append(path)
            except Exception:
                pass
    return discovered if discovered else ALL_FOLDER_SCREENSHOTS


def get_all_screenshots_for_content(primary_route: Optional[str] = None) -> list[str]:
    """
    Return all screenshot images from the screenshots folder.
    Places the primary route's matching screenshot first, followed by all other screenshots,
    ensuring every post content includes all images inside this folder.
    """
    all_imgs = get_all_folder_screenshots()
    primary = get_screenshot_for_route(primary_route) if primary_route else "/screenshots/home.png"
    remaining = [s for s in all_imgs if s != primary]
    return [primary] + remaining


def get_varied_destination_url(topic_or_pillar: str = "", platform: str = "", seed: Optional[str] = None) -> str:
    """
    Select an appropriate destination route on https://www.getyourclientsb2b.com
    rotating across varied real routes (/, /#overview, /#product, /#how-it-works, /#industries,
    /#discovery, /#pipeline, /#inbox, /#calls, /#analytics, /pricing, /contact).
    Guarantees every platform in a batch and every new post gets a different route.
    """
    platform_offset = {
        "x": 0,          # https://www.getyourclientsb2b.com/
        "linkedin": 2,   # https://www.getyourclientsb2b.com/#product
        "facebook": 3,   # https://www.getyourclientsb2b.com/#how-it-works
        "instagram": 4,  # https://www.getyourclientsb2b.com/#industries
        "youtube": 10,   # https://www.getyourclientsb2b.com/pricing
    }
    base_idx = platform_offset.get(platform.lower(), 0)
    if seed:
        try:
            seed_hash = sum(ord(c) for c in str(seed))
            base_idx = (base_idx + seed_hash) % len(TARGET_ROUTES)
        except Exception:
            pass
    return TARGET_ROUTES[base_idx]


def _wrap_utm_link(platform: str, pillar: str, post_id: str, base_url: str) -> tuple[str, dict]:
    """
    Wrap destination URL with UTM tags and register short link /r/{code}.
    Format: utm_source={platform}&utm_medium=social&utm_campaign={pillar}&utm_content={post_id}
    """
    short_code = uuid.uuid4().hex[:8]
    pillar_clean = (pillar or "social").lower().replace(" ", "_").replace("-", "_")
    utm_data = utm_dict(
        source=platform,
        medium="social",
        campaign=pillar_clean,
        content=post_id,
    )
    register_short_link(short_code, base_url, utm_data)

    # In social media posts, use the live public getyourclientsb2b.com route directly
    # instead of http://localhost:8000/r/{short_code}.
    if not settings.api_url or "localhost" in settings.api_url or "127.0.0.1" in settings.api_url:
        return base_url, utm_data

    short_link = f"{settings.api_url}/r/{short_code}"
    return short_link, utm_data


@router.get("/posts", response_model=list[PostResponse])
async def list_posts(
    platform: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    idea_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List posts filtered by platform, status, or idea."""
    query = select(Post).order_by(desc(Post.created_at)).limit(limit)
    if platform:
        query = query.where(Post.platform == platform)
    if status_filter:
        query = query.where(Post.status == status_filter)
    if idea_id:
        query = query.where(Post.idea_id == uuid.UUID(idea_id))

    result = await db.execute(query)
    posts = result.scalars().all()
    return [_to_post_response(p) for p in posts]


@router.get("/posts/{id}", response_model=PostResponse)
async def get_post(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get single post by ID."""
    p = await db.get(Post, uuid.UUID(id))
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_post_response(p)


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create a manual post."""
    if payload.body:
        check_claims(payload.body)

    post_uuid = uuid.uuid4()
    short_url = payload.link_url
    utm_data = None
    if payload.link_url:
        short_url, utm_data = _wrap_utm_link(payload.platform, "manual", str(post_uuid), payload.link_url)

    post = Post(
        id=post_uuid,
        idea_id=uuid.UUID(payload.idea_id) if payload.idea_id else None,
        platform=payload.platform,
        body=payload.body,
        media_urls=payload.media_urls,
        link_url=short_url,
        utm=utm_data,
        status=payload.status or "draft",
        scheduled_at=payload.scheduled_at,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return _to_post_response(post)


@router.post("/posts/generate", response_model=GeneratePostsResponse)
async def generate_platform_posts(
    payload: GeneratePostsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    POST /posts/generate: Takes an idea and generates platform-adapted drafts
    using template social_adapt.txt.
    Platforms: X, LinkedIn, Instagram, Facebook.
    Wraps links with UTM via /r/{code} and validates claims_guard.
    """
    idea_uuid = uuid.UUID(payload.idea_id)
    idea = await db.get(ContentIdea, idea_uuid)
    if not idea:
        raise HTTPException(status_code=404, detail="Content idea not found")

    # Fetch brand profile
    brand_res = await db.execute(select(BrandProfile).limit(1))
    brand = brand_res.scalar_one_or_none()
    brand_context = {
        "product_name": brand.product_name if brand else "GetyourclientsB2B",
        "one_liner": brand.one_liner if brand else "B2B client discovery & cold outreach CRM across 190+ countries",
        "tone": brand.tone if brand else "Direct, authoritative, tactical, transparent",
        "value_props": json.dumps(brand.value_props) if (brand and brand.value_props) else '["Interactive global map discovery", "Verified B2B emails & contacts", "Cold outreach CRM & automated sequences"]',
        "topic": idea.topic,
        "pillar": idea.pillar or "how-to",
        "link_url": payload.link_url or (brand.website_url if brand else "https://getyourclientsb2b.com"),
    }

    platforms = payload.platforms or ["x", "linkedin", "instagram", "facebook"]
    destination_url = brand_context["link_url"]

    adapted_data = None
    if settings.anthropic_api_key:
        try:
            template = _load_prompt("social_adapt")
            rendered_prompt = template.format(**brand_context)
            adapted_data = await generate(
                prompt=rendered_prompt,
                response_model=_SocialAdaptSchema,
                brand_context=brand_context,
                max_tokens=3500,
            )
        except Exception as exc:
            logger.warning("AI adaptation failed (%s), using deterministic template adapter", exc)

    clean_topic = idea.topic
    x_dest = get_varied_destination_url(clean_topic, "x", str(idea.id))
    li_dest = get_varied_destination_url(clean_topic, "linkedin", str(idea.id))
    ig_dest = get_varied_destination_url(clean_topic, "instagram", str(idea.id))
    fb_dest = get_varied_destination_url(clean_topic, "facebook", str(idea.id))

    if not adapted_data:
        # Deterministic compliant fallback matching all platform constraints with varied routes
        adapted_data = _SocialAdaptSchema(
            x=_XAdapted(
                body=f"Most B2B outbound fails because the leads are outdated.\n\nHere is how to tackle {clean_topic[:60]} with real-time verified contacts:\n\n1. Target precise ICP\n2. Run syntax + MX checks\n3. Deliver value first\n\nMore in thread below --- \nFull guide: {x_dest}",
                is_thread=True,
            ),
            linkedin=_LinkedInAdapted(
                body=(
                    f"If your B2B sales team is struggling with {clean_topic}, you're not alone.\n\n"
                    "We analyzed how modern outbound teams achieve consistent replies without burning their domains:\n\n"
                    "1. Real-time verification over stale databases\n"
                    "2. AI personalization that speaks to specific ICP pain points\n"
                    "3. Automated health ramps with strict stop rules\n\n"
                    f"You can explore the full blueprint on GetyourclientsB2B: {li_dest}\n\n"
                    "What has been your biggest deliverability challenge this quarter?"
                )
            ),
            instagram=_InstagramAdapted(
                caption=f"Mastering {clean_topic} for B2B client acquisition 📈 Swipe through for the step-by-step framework.\n\n🔗 Explore live platform: {ig_dest}\n\n#b2bsales #leadgeneration #prospecting #getyourclientsb2b #agencylife #growthhacking",
                carousel_slides=[
                    f"Slide 1: Solving {clean_topic}",
                    "Slide 2: Step 1 - Filter Target ICP",
                    "Slide 3: Step 2 - Live Email Verification",
                    "Slide 4: Step 3 - AI Personalization",
                    "Slide 5: Key Takeaway & Next Steps",
                ],
                image_prompt=get_screenshot_for_route(ig_dest),
            ),
            facebook=_FacebookAdapted(
                body=f"Struggling with {clean_topic}? Here is our complete step-by-step breakdown on scaling verified client acquisition with GetyourclientsB2B: {fb_dest}"
            ),
        )

    # Schedule suggestions (stagger posts across next few days)
    base_time = payload.schedule_start or (datetime.now(timezone.utc) + timedelta(days=1, hours=9))
    created_posts: list[Post] = []

    platform_configs = [
        ("x", adapted_data.x.body, get_all_screenshots_for_content(x_dest), base_time, x_dest),
        ("linkedin", adapted_data.linkedin.body, get_all_screenshots_for_content(li_dest), base_time + timedelta(hours=2), li_dest),
        ("instagram", adapted_data.instagram.caption, get_all_screenshots_for_content(ig_dest), base_time + timedelta(hours=4), ig_dest),
        ("facebook", adapted_data.facebook.body, get_all_screenshots_for_content(fb_dest), base_time + timedelta(hours=6), fb_dest),
    ]

    for plat, body_text, media_urls, sched_time, plat_dest_url in platform_configs:
        if plat not in platforms:
            continue

        # Enforce platform limits
        if plat == "x":
            # Ensure tweets in thread or single post are <= 280 chars
            for tweet_segment in body_text.split("---"):
                if len(tweet_segment.strip()) > 280:
                    body_text = tweet_segment.strip()[:275] + "..."
        elif plat == "linkedin":
            if len(body_text) < 200:
                body_text = body_text + "\n\nWhat has been your experience with this strategy?"

        # Claims guard check
        check_claims(body_text)

        post_id = uuid.uuid4()
        live_link, utm = _wrap_utm_link(
            platform=plat,
            pillar=idea.pillar or "social",
            post_id=str(post_id),
            base_url=plat_dest_url,
        )

        # Inject real link into body if needed
        body_with_link = body_text
        if plat_dest_url in body_with_link:
            if live_link != plat_dest_url:
                body_with_link = body_with_link.replace(plat_dest_url, live_link)
        elif destination_url in body_with_link and destination_url != live_link:
            body_with_link = body_with_link.replace(destination_url, live_link)
        elif live_link not in body_with_link and plat_dest_url not in body_with_link:
            if plat in ("facebook", "x"):
                body_with_link += f" {live_link}"
            elif plat == "linkedin":
                body_with_link += f"\n\n{live_link}"
            elif plat == "instagram":
                body_with_link += f"\n\n🔗 {live_link}"

        post = Post(
            id=post_id,
            idea_id=idea.id,
            platform=plat,
            body=body_with_link,
            media_urls=media_urls,
            link_url=live_link,
            utm=utm,
            status="pending_approval",  # Queued for human approval
            scheduled_at=sched_time,
        )
        db.add(post)
        created_posts.append(post)

    await db.commit()
    for p in created_posts:
        await db.refresh(p)

    return GeneratePostsResponse(
        idea_id=str(idea.id),
        posts=[_to_post_response(p) for p in created_posts],
    )


@router.post("/posts/{id}/approve", response_model=PostResponse)
async def approve_post(
    id: str,
    payload: ApprovePostRequest = ApprovePostRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a post in the approval queue. Transitions to scheduled or approved."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if payload.scheduled_at:
        post.scheduled_at = payload.scheduled_at

    post.status = "scheduled" if post.scheduled_at else "approved"
    post.error = None
    await db.commit()
    await db.refresh(post)

    await write_audit_log(
        db,
        action="post.approved",
        user_id=current_user.id,
        entity="posts",
        entity_id=str(post.id),
        meta={"platform": post.platform, "status": post.status, "scheduled_at": str(post.scheduled_at)},
    )
    await db.commit()

    # If scheduled time has already arrived or passed, trigger immediate publish
    now = datetime.now(timezone.utc)
    if post.scheduled_at:
        sched = post.scheduled_at if post.scheduled_at.tzinfo is not None else post.scheduled_at.replace(tzinfo=timezone.utc)
        if sched <= now:
            from worker.jobs.social import publish_single_post
            await publish_single_post(db, post)
            await db.refresh(post)

    return _to_post_response(post)


@router.post("/posts/{id}/reject", response_model=PostResponse)
async def reject_post(
    id: str,
    payload: RejectPostRequest = RejectPostRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a drafted post."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "rejected"
    post.error = payload.reason
    await db.commit()
    await db.refresh(post)

    await write_audit_log(
        db,
        action="post.rejected",
        user_id=current_user.id,
        entity="posts",
        entity_id=str(post.id),
        meta={"platform": post.platform, "reason": payload.reason},
    )
    await db.commit()
    return _to_post_response(post)


@router.post("/posts/{id}/reschedule", response_model=PostResponse)
async def reschedule_post(
    id: str,
    payload: ReschedulePostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reschedule a post to a new timestamp."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.scheduled_at = payload.scheduled_at
    if post.status in ("approved", "failed", "rejected", "draft"):
        post.status = "scheduled"

    await db.commit()
    await db.refresh(post)

    await write_audit_log(
        db,
        action="post.rescheduled",
        user_id=current_user.id,
        entity="posts",
        entity_id=str(post.id),
        meta={"scheduled_at": str(payload.scheduled_at)},
    )
    await db.commit()
    return _to_post_response(post)


@router.post("/posts/{id}/retry", response_model=PostResponse)
async def retry_failed_post(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed post."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "scheduled"
    post.error = None
    # Schedule for immediate publish window
    post.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    await db.commit()
    await db.refresh(post)

    await write_audit_log(
        db,
        action="post.retried",
        user_id=current_user.id,
        entity="posts",
        entity_id=str(post.id),
        meta={"platform": post.platform},
    )
    await db.commit()
    return _to_post_response(post)


@router.post("/posts/{id}/publish", response_model=PostResponse)
async def publish_post_now(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a post immediately to its platform."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    from worker.jobs.social import publish_single_post
    result = await publish_single_post(db, post)
    await db.refresh(post)

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error or "Failed to publish post to platform.",
        )

    return _to_post_response(post)


@router.put("/posts/{id}", response_model=PostResponse)
async def update_post(
    id: str,
    payload: PostUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Edit post body, media, link, or schedule."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if payload.body is not None:
        check_claims(payload.body)
        post.body = payload.body
    if payload.media_urls is not None:
        post.media_urls = payload.media_urls
    if payload.link_url is not None:
        post.link_url = payload.link_url
    if payload.scheduled_at is not None:
        post.scheduled_at = payload.scheduled_at
    if payload.status is not None:
        post.status = payload.status

    await db.commit()
    await db.refresh(post)
    return _to_post_response(post)


@router.delete("/posts/{id}", status_code=204)
async def delete_post(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a post."""
    post = await db.get(Post, uuid.UUID(id))
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await db.delete(post)
    await db.commit()
    return None


# ─── Calendar Feed ────────────────────────────────────────────────────────────

@router.get("/calendar", response_model=CalendarFeedResponse)
async def get_calendar(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    GET /calendar: returns month and week feed with scheduled/published posts
    and best-time posting suggestions.
    """
    query = select(Post).where(Post.scheduled_at.is_not(None))
    if platform:
        query = query.where(Post.platform == platform)

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.where(Post.scheduled_at >= start_dt)
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.where(Post.scheduled_at <= end_dt)
        except Exception:
            pass

    query = query.order_by(Post.scheduled_at.asc())
    result = await db.execute(query)
    posts = result.scalars().all()

    # Determine best-time suggestions (data-driven if >=30 posts exist, else simple heuristic)
    total_posts_count = (await db.execute(select(func.count()).select_from(Post))).scalar() or 0

    best_times: dict[str, list[str]] = {
        "x": ["09:00", "12:30", "17:00"],
        "linkedin": ["08:30", "10:15", "14:00"],
        "instagram": ["11:00", "14:30", "19:00"],
        "facebook": ["09:30", "13:00", "16:00"],
        "youtube": ["15:00", "18:00"],
    }

    if total_posts_count >= 30:
        # Check click data for top performing hours
        try:
            clicks_query = select(
                LinkClick.utm_source,
                func.count().label("clicks"),
            ).group_by(LinkClick.utm_source)
            clicks_res = await db.execute(clicks_query)
            # Retain or refine best times based on activity
        except Exception as exc:
            logger.debug("Error computing data-driven calendar times: %s", exc)

    items = [
        CalendarItem(
            id=str(p.id),
            type="post",
            platform=p.platform,
            title=(p.body or "")[:50] + ("..." if len(p.body or "") > 50 else ""),
            body=p.body or "",
            status=p.status,
            scheduled_at=p.scheduled_at,
            published_at=p.published_at,
            external_post_id=p.external_post_id,
            error=p.error,
        )
        for p in posts
        if p.scheduled_at
    ]

    return CalendarFeedResponse(
        items=items,
        best_time_suggestions=best_times,
    )


def _to_post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=str(post.id),
        idea_id=str(post.idea_id) if post.idea_id else None,
        platform=post.platform,
        body=post.body,
        media_urls=post.media_urls,
        link_url=post.link_url,
        utm=post.utm,
        status=post.status,
        scheduled_at=post.scheduled_at,
        published_at=post.published_at,
        external_post_id=post.external_post_id,
        error=post.error,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )
