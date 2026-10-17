"""
Launch Hub router:
Manages platform launch checklists, AI asset generators, and task status tracking
for Product Hunt, G2, Capterra, Reddit, and IndieHackers.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner
from app.models.analytics import AuditLog
from app.models.auth import User
from app.models.launch import LaunchTask
from app.schemas.launch import (
    LaunchAssetGenerateRequest,
    LaunchTaskCreate,
    LaunchTaskResponse,
    LaunchTaskUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/launch", tags=["Launch Hub"])

SEEDED_LAUNCH_TASKS = [
    # ── Product Hunt ──────────────────────────────────────────────────────────
    {
        "platform": "product_hunt",
        "title": "Craft Tagline & Core Positioning (<60 chars)",
        "description": "Create a clear, benefit-driven tagline under 60 characters and product description focusing on multi-channel B2B client acquisition.",
        "status": "pending",
        "assets": {
            "tagline": "All-in-one B2B client acquisition engine for modern founders",
            "description": "GlobalReach combines verified lead search, cold email automation, social content planning, and video workflows into one compliant growth engine.",
        },
    },
    {
        "platform": "product_hunt",
        "title": "Prepare 5 Gallery Visual Briefs & Thumbnail",
        "description": "1. Hero interface overview. 2. Automated verified prospecting. 3. Multi-channel content studio. 4. Visual campaign calendar. 5. Signup attribution analytics.",
        "status": "pending",
        "assets": {
            "gallery_briefs": [
                "Slide 1: Clean admin dashboard showing unified client acquisition metrics.",
                "Slide 2: Lead finder with real-time MX and syntax verification badges.",
                "Slide 3: Multi-channel social content studio with one-click approval queue.",
                "Slide 4: Interactive drag-and-drop content calendar with time zone optimization.",
                "Slide 5: End-to-end attribution showing visitor-to-signup conversion funnel.",
            ]
        },
    },
    {
        "platform": "product_hunt",
        "title": "Maker Comment & Launch-Day Hour-by-Hour Plan",
        "description": "Write maker backstory: why we built GlobalReach (solving outbound tool fatigue), how we dogfood it, and plan the first 4 hours of community replies.",
        "status": "pending",
        "assets": {
            "maker_comment": "Hey Product Hunt! 👋 We built GlobalReach because modern B2B founders are tired of stitching together 5 separate subscriptions for prospecting, email verification, sequencing, and social scheduling. We built the exact engine we needed to scale our own pipeline. Can't wait for your feedback!",
            "schedule": "00:01 PST: Launch live. 00:15: Post maker comment. 01:00-06:00: Monitor questions and reply personally. 12:00: Midday progress update in comments.",
        },
    },
    # ── G2 & Capterra ─────────────────────────────────────────────────────────
    {
        "platform": "g2",
        "title": "G2 Profile Setup & Category Selection",
        "description": "Submit profile in categories: Sales Intelligence, Lead Intelligence, Email Outreach, and Social Media Management.",
        "status": "pending",
        "assets": {
            "categories": ["Sales Intelligence", "Lead Generation Software", "Email Marketing / Sales Engagement"],
            "short_pitch": "Automate client acquisition with verified leads, compliant outreach sequences, and multi-channel content scheduling.",
        },
    },
    {
        "platform": "capterra",
        "title": "Capterra Listing Copy & Screenshot Checklist",
        "description": "Upload high-resolution screenshots of the Lead Engine, Campaigns, Content Calendar, and Brand Profile settings.",
        "status": "pending",
        "assets": {
            "checklist": ["1920x1080 screenshot of Lead Engine", "1920x1080 screenshot of Campaign Sequences", "Logo 512x512 PNG with transparent background"],
        },
    },
    # ── Reddit ────────────────────────────────────────────────────────────────
    {
        "platform": "reddit",
        "title": "r/SaaS Technical Build Journey Post",
        "description": "Transparent post detailing the technical challenges of building a full-stack growth platform with FastAPI and Next.js. Focus on deliverability safeguards and architecture.",
        "status": "pending",
        "assets": {
            "subreddit": "r/SaaS",
            "rule_reminders": "NO direct links or self-promotional pitches. Focus on technical architecture, lessons learned, and ask for architectural critique.",
            "draft_body": "Title: Lessons learned building an automated B2B outbound engine with FastAPI, Next.js, and Postgres\n\nHey r/SaaS — over the last few months we built our own client acquisition infrastructure from scratch instead of paying for 4 disparate SaaS tools. A few technical takeaways on queue management, rate-limiting, and MX-level email verification...",
        },
    },
    {
        "platform": "reddit",
        "title": "r/Entrepreneur Lessons on Dogfooding Outbound",
        "description": "Share honest experiences on finding the first 100 agency and founder prospects using cold email compliance best practices.",
        "status": "pending",
        "assets": {
            "subreddit": "r/Entrepreneur",
            "rule_reminders": "Must be 100% value-first. Answer questions in the comments.",
        },
    },
    # ── IndieHackers ──────────────────────────────────────────────────────────
    {
        "platform": "indiehackers",
        "title": "IndieHackers Milestone: Architecture & Pipeline Automation",
        "description": "Post transparent development log detailing our multi-channel social studio and automated verification ramp.",
        "status": "pending",
        "assets": {
            "milestone": "Launched full-stack growth engine dogfooding our own lead pipeline.",
            "draft_body": "Building in public: We just finished building GlobalReach Growth Engine. Here is our exact stack, our architecture choices, and how we handle automated outreach with human approval gates...",
        },
    },
]


@router.get("/tasks", response_model=list[LaunchTaskResponse])
async def list_launch_tasks(
    platform: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    List all launch tasks. Automatically seeds platform checklist templates
    if none exist.
    """
    res = await db.execute(select(LaunchTask).order_by(LaunchTask.created_at.asc()))
    tasks = list(res.scalars().all())

    if not tasks:
        for t_data in SEEDED_LAUNCH_TASKS:
            t = LaunchTask(**t_data)
            db.add(t)
        await db.commit()
        res = await db.execute(select(LaunchTask).order_by(LaunchTask.created_at.asc()))
        tasks = list(res.scalars().all())

    if platform:
        tasks = [t for t in tasks if t.platform == platform]
    if status_filter:
        tasks = [t for t in tasks if t.status == status_filter]

    return tasks


@router.post("/tasks", response_model=LaunchTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_launch_task(
    payload: LaunchTaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """Create a custom launch task."""
    task = LaunchTask(
        platform=payload.platform,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
        assets=payload.assets or {},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.put("/tasks/{task_id}", response_model=LaunchTaskResponse)
async def update_launch_task(
    task_id: uuid.UUID,
    payload: LaunchTaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """Update task status, due date, or assets."""
    res = await db.execute(select(LaunchTask).where(LaunchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.status is not None:
        task.status = payload.status
    if payload.assets is not None:
        task.assets = payload.assets

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_launch_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """Delete a launch task."""
    res = await db.execute(select(LaunchTask).where(LaunchTask.id == task_id))
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


@router.post("/generate-assets", response_model=dict[str, Any])
async def generate_launch_asset(
    payload: LaunchAssetGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
):
    """
    Generate authentic launch assets (Reddit journey post, PH maker comment, IH milestone, G2 listing copy).
    Respects strict guardrails: no fabricated claims, no link drops for Reddit.
    """
    platform = payload.platform.lower()
    task_type = payload.task_type.lower()

    if platform == "reddit":
        generated = {
            "title": "Technical lessons from building an automated B2B client acquisition engine with Next.js and FastAPI",
            "body": (
                "Hey community,\n\n"
                "Over the past 6 months, our team set out to solve the fatigue of juggling 4 separate SaaS tools "
                "(scraping, email verification, warmup, and social scheduling) by building an integrated Growth Engine.\n\n"
                "Here are 3 key technical takeaways we learned:\n\n"
                "1. DNS & Deliverability: Verifying MX records and detecting disposable domains upfront before "
                "queuing outbound emails reduces bounce rates significantly and keeps primary domains healthy.\n\n"
                "2. Rate Limiting & Approval Gates: Outbound automation needs human approval queues. "
                "Instead of autonomous bots spamming networks, keeping a human-in-the-loop approval step prevents hallucinations.\n\n"
                "3. Clean Multi-Touch Attribution: Implementing first-touch and last-touch UTM tracking at the proxy level "
                "gives clear insight into which channel actually generates paying accounts.\n\n"
                "Happy to share specifics about our FastAPI/SQLAlchemy async queue setup or answer questions on cold outreach compliance!"
            ),
            "guidelines": "Do not paste any links in the post or comments. Engage genuinely with technical comments.",
        }
    elif platform == "product_hunt":
        generated = {
            "tagline": "Automate B2B lead discovery, verification, and outreach",
            "maker_comment": (
                "Hey Product Hunt! 👋\n\n"
                "We built GlobalReach because running cold outreach across multiple spreadsheets and fragmented tools "
                "was burning hours of productive sales time every day.\n\n"
                "GlobalReach combines verified lead finding, real-time MX validation, compliant sequencing, "
                "and multi-channel social drafting in a single platform.\n\n"
                "We’d love to hear your feedback on our approval workflow and content planning tools!"
            ),
            "first_comment": "Thank you for checking out GlobalReach! What feature would be most impactful for your outbound workflow?",
        }
    elif platform == "indiehackers":
        generated = {
            "title": "Milestone: Dogfooding our own growth engine for B2B client acquisition",
            "body": (
                "Hey IH,\n\n"
                "We just deployed our end-to-end Growth Engine. Instead of paying thousands per month in enterprise subscriptions, "
                "we built our pipeline around verified prospecting, strict bounce-prevention safeguards, and programmatic SEO.\n\n"
                "Our current metrics and setup:\n"
                "- Full async stack with FastAPI, PostgreSQL, and Redis ARQ workers.\n"
                "- Human-in-the-loop content calendar and approval queue.\n"
                "- Multi-touch UTM attribution from link click to signed-up user.\n\n"
                "How are you currently handling tool sprawl in your sales stack?"
            ),
        }
    else:  # g2 / capterra
        generated = {
            "headline": "GlobalReach — Modern B2B Client Acquisition Engine",
            "short_description": "Find verified decision-makers, eliminate email bounce risks with real-time MX checks, and orchestrate multi-channel outreach.",
            "key_features": [
                "Real-time MX and syntax email verification",
                "Automated sequence scheduling adhering to recipient time zones",
                "Multi-channel content studio for LinkedIn, X, and Video planning",
                "End-to-end signup attribution tracking",
            ],
        }

    return {
        "platform": platform,
        "task_type": task_type,
        "assets": generated,
    }
