"""
Public Lead-Magnet Free Tools router:
1. Subject Line Grader (scores 0-100, feedback reasons, 3 AI rewrites, rate limited by IP)
2. Email Verifier (syntax, MX, disposable, role; 5/day per IP limit with email capture unlock)
Logs all usages to tool_usages with captured email and UTM.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.seo import ToolUsage
from app.schemas.tools import (
    EmailVerifyToolRequest,
    EmailVerifyToolResponse,
    SubjectGradeRequest,
    SubjectGradeResponse,
    SubjectRewrite,
)
from app.services.email_verify import verify_email
from app.services.ratelimit import make_rate_limiter
from app.services.utm import build_utm_url

router = APIRouter(prefix="/public/tools", tags=["Public Free Tools"])
admin_tools_router = APIRouter(prefix="/tools", tags=["Tools Admin"])

# Spam words trigger list
SPAM_WORDS = {
    "free", "guarantee", "guaranteed", "buy now", "urgent", "100%", "risk free",
    "act now", "order now", "special promotion", "winner", "cash", "save $",
    "make money", "miracle", "no cost", "pure profit", "unlimited", "congratulations",
}


def _grade_subject_line(subject: str) -> tuple[int, list[str], dict[str, Any]]:
    """Heuristic scoring of cold email subject line."""
    score = 75
    reasons = []
    char_len = len(subject.strip())
    words = subject.strip().split()
    word_count = len(words)

    # 1. Length analysis (optimal: 3-7 words / 20-45 chars)
    if 20 <= char_len <= 45 and 3 <= word_count <= 7:
        reasons.append("Optimal length: Short and punchy (under 45 characters)")
        score += 15
    elif char_len > 60:
        reasons.append(f"Subject line is too long ({char_len} chars). It may get truncated on mobile devices.")
        score -= 15
    elif word_count <= 2:
        reasons.append("Very short: High open rate but make sure context is clear.")
        score += 5

    # 2. Spam words check
    subject_lower = subject.lower()
    found_spam = [word for word in SPAM_WORDS if word in subject_lower]
    if found_spam:
        reasons.append(f"Spam trigger alert: Detected words ({', '.join(found_spam[:2])}) that harm deliverability.")
        score -= 25
    else:
        reasons.append("Clean deliverability: Zero common spam trigger words detected.")
        score += 5

    # 3. Personalization tokens
    has_token = bool(re.search(r"\{\{.*?\}\}|\[.*?\]", subject))
    if has_token:
        reasons.append("High personalization: Contains dynamic prospect tags.")
        score += 10
    else:
        reasons.append("Tip: Adding {{first_name}} or {{company}} can boost open rates by up to 22%.")

    # 4. Case analysis (all caps penalty)
    if subject.isupper() and len(subject) > 5:
        reasons.append("Critical: ALL CAPS triggers aggressive spam filters.")
        score -= 30
    elif subject.islower():
        reasons.append("Casual lowercase style: Proven to increase executive B2B open rates.")
        score += 5

    # 5. Question / Curiosity
    if "?" in subject:
        reasons.append("Curiosity hook: Questions encourage decision-makers to open.")
        score += 5

    final_score = max(10, min(98, score))
    input_stats = {
        "character_count": char_len,
        "word_count": word_count,
        "spam_triggers_found": found_spam,
        "has_personalization": has_token,
    }
    return final_score, reasons, input_stats


def _generate_rewrites(subject: str, industry: str | None = None) -> list[SubjectRewrite]:
    """Generate 3 high-converting cold email rewrites."""
    ind = industry or "B2B"
    return [
        SubjectRewrite(
            style="Short & Casual",
            subject=f"quick question re: {{{{company}}}}",
            why_it_works="Looks like an internal email from a colleague or peer; dramatically reduces guard.",
        ),
        SubjectRewrite(
            style="Curiosity & Insight",
            subject=f"ideas for {{{{company}}}}'s {ind} pipeline",
            why_it_works="Offers specific industry value without sounding like a generic sales pitch.",
        ),
        SubjectRewrite(
            style="Personalized & Direct",
            subject=f"finding verified leads for {{{{company}}}}",
            why_it_works="Cuts straight to the core workflow benefit tailored to their brand.",
        ),
    ]


@router.post(
    "/subject-grader",
    response_model=SubjectGradeResponse,
    dependencies=[Depends(make_rate_limiter(max_requests=30, window_seconds=60))],
)
async def grade_subject_line_endpoint(
    payload: SubjectGradeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public free tool: Scores cold email subject line from 0 to 100,
    provides reasons, 3 AI rewrites, and CTA.
    """
    score, reasons, input_stats = _grade_subject_line(payload.subject_line)
    rewrites = _generate_rewrites(payload.subject_line, payload.industry_context)

    # Hash input for privacy
    inp_hash = hashlib.sha256(payload.subject_line.strip().encode()).hexdigest()

    # Log tool usage
    utm_data = {
        "utm_source": payload.utm_source or "growth_engine_tools",
        "utm_medium": payload.utm_medium or "free_tool",
        "utm_campaign": payload.utm_campaign or "subject_grader",
    }
    usage = ToolUsage(
        tool_slug="subject-grader",
        input_hash=inp_hash,
        email_captured=payload.email_captured,
        utm=utm_data,
    )
    db.add(usage)
    await db.commit()

    cta_link = build_utm_url(
        "https://www.getyourclientsb2b.com/signup",
        source=utm_data["utm_source"],
        medium=utm_data["utm_medium"],
        campaign=utm_data["utm_campaign"],
        content="subject_grader_result",
    )

    return SubjectGradeResponse(
        score=score,
        reasons=reasons,
        rewrites=rewrites,
        input_stats=input_stats,
        cta={
            "headline": "Find and email verified leads in GlobalReach",
            "subheadline": "Stop bouncing. Automated lead search and multi-channel outreach in one engine.",
            "button_text": "Claim Your Free GlobalReach Leads",
            "url": cta_link,
        },
    )


@router.post(
    "/email-verifier",
    response_model=EmailVerifyToolResponse,
    dependencies=[Depends(make_rate_limiter(max_requests=40, window_seconds=60))],
)
async def verify_email_tool_endpoint(
    payload: EmailVerifyToolRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public free tool: Verify one email address.
    Limits to 5 per day per IP. If exceeded without email capture, prompts for email unlock.
    """
    client_ip = request.client.host if request.client else "unknown"
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check daily usage for this IP
    ip_hash = hashlib.sha256(f"{client_ip}:{today_start.date()}".encode()).hexdigest()
    res = await db.execute(
        select(func.count())
        .select_from(ToolUsage)
        .where(
            ToolUsage.tool_slug == "email-verifier",
            ToolUsage.input_hash.like(f"{ip_hash[:16]}%"),
            ToolUsage.created_at >= today_start,
        )
    )
    daily_count = res.scalar() or 0

    DAILY_LIMIT = 5
    requires_unlock = daily_count >= DAILY_LIMIT and not payload.email_captured
    if requires_unlock:
        # Prompt user for email capture to continue
        cta_link = build_utm_url(
            "https://www.getyourclientsb2b.com/signup",
            source="growth_engine_tools",
            medium="free_tool",
            campaign="email_verifier_gate",
            content="limit_reached",
        )
        return EmailVerifyToolResponse(
            email=payload.email,
            syntax_ok=True,
            mx_ok=False,
            is_disposable=False,
            is_role=False,
            status="locked",
            notes=["Daily limit of 5 free checks reached. Enter your email to unlock unlimited verifications or start in GlobalReach."],
            daily_checks_remaining=0,
            requires_email_unlock=True,
            cta={
                "headline": "Find and email verified leads in GlobalReach",
                "subheadline": "Verify thousands of emails in bulk with zero bounce risk.",
                "button_text": "Unlock Unlimited Verifications",
                "url": cta_link,
            },
        )

    # Run verification service
    result = await verify_email(payload.email)

    # Log usage
    utm_data = {
        "utm_source": payload.utm_source or "growth_engine_tools",
        "utm_medium": payload.utm_medium or "free_tool",
        "utm_campaign": payload.utm_campaign or "email_verifier",
    }
    compound_hash = f"{ip_hash[:16]}_{hashlib.sha256(payload.email.strip().encode()).hexdigest()[:16]}"
    usage = ToolUsage(
        tool_slug="email-verifier",
        input_hash=compound_hash,
        email_captured=payload.email_captured,
        utm=utm_data,
    )
    db.add(usage)
    await db.commit()

    remaining = max(0, DAILY_LIMIT - (daily_count + 1))
    cta_link = build_utm_url(
        "https://www.getyourclientsb2b.com/signup",
        source=utm_data["utm_source"],
        medium=utm_data["utm_medium"],
        campaign=utm_data["utm_campaign"],
        content="verifier_result",
    )

    return EmailVerifyToolResponse(
        email=payload.email,
        syntax_ok=result["syntax_ok"],
        mx_ok=result["mx_ok"],
        is_disposable=result["is_disposable"],
        is_role=result["is_role"],
        status=result["status"],
        notes=result["notes"],
        daily_checks_remaining=remaining,
        requires_email_unlock=False,
        cta={
            "headline": "Find and email verified leads in GlobalReach",
            "subheadline": "Tired of manual single-checks? Prospect and verify thousands of B2B emails automatically.",
            "button_text": "Verify Entire Lists in GlobalReach",
            "url": cta_link,
        },
    )


# ─── ADMIN STATS ENDPOINT ─────────────────────────────────────────────────────

@admin_tools_router.get("/overview")
async def get_tools_overview(
    db: AsyncSession = Depends(get_db),
):
    """Admin dashboard stats: total runs, email captures, and breakdown."""
    total_runs_res = await db.execute(select(func.count()).select_from(ToolUsage))
    total_runs = total_runs_res.scalar() or 0

    emails_res = await db.execute(select(func.count()).select_from(ToolUsage).where(ToolUsage.email_captured.isnot(None)))
    emails_captured = emails_res.scalar() or 0

    by_tool_res = await db.execute(select(ToolUsage.tool_slug, func.count().label("cnt")).group_by(ToolUsage.tool_slug))
    by_tool = {row.tool_slug: row.cnt for row in by_tool_res}

    return {
        "total_runs": total_runs,
        "emails_captured": emails_captured,
        "conversion_rate_pct": round((emails_captured / total_runs * 100), 2) if total_runs > 0 else 0.0,
        "by_tool": by_tool,
    }
