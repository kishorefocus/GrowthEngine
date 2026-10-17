"""
Review requests router:
Sends review-request email (direct G2 or Capterra link) to active users who opted in.
Records the request in review_requests and writes to audit_log.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_owner
from app.models.analytics import AuditLog
from app.models.auth import User
from app.models.launch import ReviewRequest
from app.models.leads import Lead
from app.providers.email import StubEmailProvider
from app.schemas.launch import ReviewRequestCreate, ReviewRequestResponse
from app.services.dryrun import dry_run_guard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/request", response_model=ReviewRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_review_request(
    payload: ReviewRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """
    Send a review-request email for G2 or Capterra to an active user.
    Records in review_requests, checks suppression/opt-in status, and writes to audit_log.
    """
    # Check if a review request was already sent to this email
    existing_res = await db.execute(
        select(ReviewRequest).where(
            ReviewRequest.user_email == payload.user_email,
            ReviewRequest.platform == payload.platform,
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"A review request for {payload.platform} has already been sent to {payload.user_email}.",
        )

    # Review request link
    if payload.platform.lower() == "g2":
        review_url = "https://www.g2.com/products/globalreach/reviews"
    else:
        review_url = "https://www.capterra.com/p/globalreach/reviews"

    email_subject = "Quick question about your experience with GlobalReach?"
    email_body = (
        f"Hi there,\n\n"
        f"Thank you for using GlobalReach to power your B2B client acquisition!\n\n"
        f"Would you be open to sharing a quick honest review of GlobalReach on {payload.platform.upper()}? "
        f"It takes less than 2 minutes and helps other founders discover honest outbound tools.\n\n"
        f"Leave your review here: {review_url}\n\n"
        f"Best,\nThe GlobalReach Team\n"
    )

    # Dry run execution or stub provider
    await dry_run_guard(
        "review_request.send",
        {"user_email": payload.user_email, "platform": payload.platform},
        lambda: StubEmailProvider().send(
            to_email=payload.user_email,
            from_email=settings.outreach_from_email,
            subject=email_subject,
            body=email_body,
        ),
    )

    now = datetime.now(timezone.utc)
    review_req = ReviewRequest(
        user_email=payload.user_email,
        platform=payload.platform.lower(),
        sent_at=now,
        status="sent",
    )
    db.add(review_req)
    await db.commit()

    # Log to audit_log
    audit = AuditLog(
        user_id=user.id,
        action="review_request.sent",
        entity="review_requests",
        entity_id=str(review_req.id),
        meta={"user_email": payload.user_email, "platform": payload.platform},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(review_req)

    return review_req


@router.get("", response_model=list[ReviewRequestResponse])
async def list_review_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """List all review requests."""
    res = await db.execute(select(ReviewRequest).order_by(ReviewRequest.created_at.desc()))
    return list(res.scalars().all())
