"""
Analytics router:
- GET /r/{code}     (public) — short-link redirect, logs click, appends UTM
- GET /analytics/overview — dashboard KPIs by channel
"""
import hashlib
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analytics import LinkClick, SignupAttribution
from app.models.analytics import AuditLog
from app.models.auth import User
from app.models.leads import EmailMessage
from app.models.social import Post
from app.models.seo import SEOPage
from app.services.ratelimit import make_rate_limiter
from app.services.utm import build_utm_url, CHANNELS

router = APIRouter(tags=["analytics"])
_public_limiter = make_rate_limiter(max_requests=120, window_seconds=60)

# In-memory short-code store (replace with DB table in production)
# short_code -> {"url": str, "utm_source": str, ...}
_short_links: dict[str, dict] = {}


def register_short_link(code: str, destination: str, utm_params: dict) -> None:
    """Register a short link code. Called when creating UTM links."""
    _short_links[code] = {"url": destination, **utm_params}


@router.get("/r/{code}", include_in_schema=False)
async def short_link_redirect(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_public_limiter),
):
    """
    Public short-link redirect.
    Logs the click in link_clicks, appends UTM params to destination URL.
    """
    link = _short_links.get(code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found.")

    visitor_id = request.cookies.get("gr_visitor_id", str(uuid.uuid4()))

    click = LinkClick(
        utm_source=link.get("utm_source"),
        utm_medium=link.get("utm_medium"),
        utm_campaign=link.get("utm_campaign"),
        utm_content=link.get("utm_content"),
        visitor_id=visitor_id,
        short_code=code,
        destination_url=link["url"],
        landed_at=datetime.now(timezone.utc),
    )
    db.add(click)
    await db.commit()

    # Build UTM-tagged destination
    destination = build_utm_url(
        base_url=link["url"],
        source=link.get("utm_source", ""),
        medium=link.get("utm_medium", ""),
        campaign=link.get("utm_campaign", ""),
        content=link.get("utm_content"),
    )

    response = RedirectResponse(url=destination, status_code=302)
    response.set_cookie("gr_visitor_id", visitor_id, max_age=60 * 60 * 24 * 365, httponly=False, samesite="lax")
    return response


@router.get("/analytics/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Dashboard analytics overview.
    Returns KPIs: visits, signups, conversion rate, channel breakdown,
    email metrics, top posts, top SEO pages.
    Returns zeros for channels that don't have data yet.
    """
    # Total visits (link clicks)
    visits_result = await db.execute(select(func.count()).select_from(LinkClick))
    total_visits = visits_result.scalar() or 0

    # Total signups
    signups_result = await db.execute(select(func.count()).select_from(SignupAttribution))
    total_signups = signups_result.scalar() or 0

    conversion_rate = round((total_signups / total_visits * 100), 2) if total_visits > 0 else 0.0

    # Channel breakdown (visits by utm_source)
    channel_query = await db.execute(
        select(LinkClick.utm_source, func.count().label("visits"))
        .group_by(LinkClick.utm_source)
        .order_by(func.count().desc())
    )
    channel_rows = channel_query.all()
    channel_visits = {row.utm_source or "direct": row.visits for row in channel_rows}

    # Signups by channel (first touch)
    signups_by_channel: dict[str, int] = {}
    signup_rows = await db.execute(select(SignupAttribution.first_touch))
    for row in signup_rows.scalars():
        if row:
            src = row.get("utm_source", "direct")
        else:
            src = "direct"
        signups_by_channel[src] = signups_by_channel.get(src, 0) + 1

    # Email metrics
    email_total = (await db.execute(select(func.count()).select_from(EmailMessage))).scalar() or 0
    email_sent = (await db.execute(
        select(func.count()).select_from(EmailMessage).where(EmailMessage.status.in_(["sent", "delivered", "opened", "clicked", "replied"]))
    )).scalar() or 0
    email_replied = (await db.execute(
        select(func.count()).select_from(EmailMessage).where(EmailMessage.status == "replied")
    )).scalar() or 0
    email_bounced = (await db.execute(
        select(func.count()).select_from(EmailMessage).where(EmailMessage.status == "bounced")
    )).scalar() or 0

    reply_rate = round((email_replied / email_sent * 100), 2) if email_sent > 0 else 0.0
    bounce_rate = round((email_bounced / email_sent * 100), 2) if email_sent > 0 else 0.0

    # Top posts
    top_posts_result = await db.execute(
        select(Post).where(Post.status == "published").order_by(Post.published_at.desc()).limit(5)
    )
    top_posts = [
        {"id": str(p.id), "platform": p.platform, "body_preview": (p.body or "")[:80], "published_at": str(p.published_at)}
        for p in top_posts_result.scalars()
    ]

    # Top SEO pages
    top_seo_result = await db.execute(
        select(SEOPage).where(SEOPage.status == "published").order_by(SEOPage.quality_score.desc().nullslast()).limit(5)
    )
    top_seo = [
        {"id": str(p.id), "slug": p.slug, "title": p.title, "quality_score": p.quality_score}
        for p in top_seo_result.scalars()
    ]

    # Build full channel table with zeros for channels with no data
    all_channels = {ch: 0 for ch in CHANNELS}
    all_channels.update(channel_visits)

    return {
        "overview": {
            "total_visits": total_visits,
            "total_signups": total_signups,
            "conversion_rate_pct": conversion_rate,
        },
        "email": {
            "total_scheduled": email_total,
            "sent": email_sent,
            "reply_rate_pct": reply_rate,
            "bounce_rate_pct": bounce_rate,
        },
        "channels": all_channels,
        "signups_by_channel": signups_by_channel,
        "top_posts": top_posts,
        "top_seo_pages": top_seo,
    }
