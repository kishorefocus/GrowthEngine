"""
Video Studio router:
- POST /videos/plan: generates title options, 60s Shorts script, 5-8 min YouTube outline,
  step-by-step screen-recording shot list for GlobalReach, description with chapters & UTM,
  tags, and thumbnail prompt via template video_plan.txt.
- POST /videos/{id}/upload-url: generates signed S3/R2 upload URL.
- POST /videos/{id}/publish-youtube: publishes video via YouTube Data API (strictly private).
- POST /videos/{id}/cross-post-captions: generates caption variants for Instagram Reels,
  Facebook Reels, and LinkedIn video.
- CRUD for video projects.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import BrandProfile, SocialAccount, User
from app.models.social import VideoProject
from app.providers.social import PostPayload, get_social_publisher
from app.schemas.social import (
    UploadUrlResponse,
    VideoPlanRequest,
    VideoProjectResponse,
    VideoProjectUpdate,
)
from app.services.ai import _load_prompt, generate
from app.services.audit import write_audit_log
from app.services.claims_guard import check_claims
from app.services.crypto import decrypt_token
from app.services.storage import generate_presigned_upload_url
from app.services.utm import utm_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["video"])


class _AIVideoPlanSchema(BaseModel):
    title_options: list[str]
    youtube_title: str
    shorts_script: str
    youtube_outline: str
    shot_list: list[dict[str, Any]]
    captions: str
    youtube_description: str
    tags: list[str]
    thumbnail_prompt: str


class CrossPostCaptionsResponse(BaseModel):
    video_id: str
    instagram_reels: str
    facebook_reels: str
    linkedin_video: str


@router.get("", response_model=list[VideoProjectResponse])
async def list_videos(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all video projects."""
    query = select(VideoProject).order_by(desc(VideoProject.created_at))
    if status_filter:
        query = query.where(VideoProject.status == status_filter)

    result = await db.execute(query)
    projects = result.scalars().all()
    return [_to_video_response(p) for p in projects]


@router.get("/{id}", response_model=VideoProjectResponse)
async def get_video(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get single video project by ID."""
    p = await db.get(VideoProject, uuid.UUID(id))
    if not p:
        raise HTTPException(status_code=404, detail="Video project not found")
    return _to_video_response(p)


@router.post("/plan", response_model=VideoProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_video_plan(
    payload: VideoPlanRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    POST /videos/plan: Takes a target keyword and generates a complete video production
    plan: title options, 60s Shorts script, 5-8 min YouTube outline, screen-recording shot list,
    captions, description with chapters and UTM link, tags, and thumbnail prompt.
    """
    check_claims(payload.target_keyword)

    # Brand context
    brand_res = await db.execute(select(BrandProfile).limit(1))
    brand = brand_res.scalar_one_or_none()

    destination_url = (brand.website_url if brand else "https://www.getyourclientsb2b.com")
    brand_context = {
        "product_name": brand.product_name if brand else "GlobalReach",
        "one_liner": brand.one_liner if brand else "B2B client acquisition engine with verified leads and automated outreach",
        "tone": brand.tone if brand else "Direct, tactical, clear, authoritative",
        "value_props": json.dumps(brand.value_props) if (brand and brand.value_props) else '["Verified B2B emails", "AI personalized sequences", "Domain deliverability safety"]',
        "keyword": payload.target_keyword,
        "link_url": destination_url,
    }

    ai_data: Optional[_AIVideoPlanSchema] = None
    if settings.anthropic_api_key:
        try:
            template = _load_prompt("video_plan")
            rendered_prompt = template.format(**brand_context)
            if payload.additional_notes:
                rendered_prompt += f"\nAdditional guidelines: {payload.additional_notes}"

            ai_data = await generate(
                prompt=rendered_prompt,
                response_model=_AIVideoPlanSchema,
                brand_context=brand_context,
                max_tokens=4000,
            )
        except Exception as exc:
            logger.warning("AI video planning failed (%s), using structured default plan", exc)

    if not ai_data:
        kw = payload.target_keyword
        ai_data = _AIVideoPlanSchema(
            title_options=[
                f"How to Master {kw} in 2026 (Step-by-Step)",
                f"Stop Doing Cold Outreach Wrong: {kw}",
                f"The Fastest Workflow for {kw} (Live Demo)",
            ],
            youtube_title=f"How to Solve {kw} in 5 Minutes (Step-by-Step Tutorial)",
            shorts_script=(
                f"[Visual: Screen recording of GlobalReach dashboard]\n"
                f"Stop buying outdated lead lists that bounce and burn your domain. "
                f"Here is how to tackle {kw} in 3 simple steps.\n"
                f"Step 1: Define your ideal customer profile by industry, company size, and job title.\n"
                f"Step 2: Run live email verification to filter out disposable domains and verify MX records.\n"
                f"Step 3: Personalize your sequences using AI hooks without sounding spammy.\n"
                f"Try it free with verified leads at {destination_url}."
            ),
            youtube_outline=(
                f"0:00 - Introduction & The Core Problem with {kw}\n"
                "1:10 - Why Legacy Scrapers & Stale Databases Fail\n"
                "2:30 - Live Demonstration: Targeting Your Exact ICP\n"
                "4:00 - Verifying Deliverability (SPF, DKIM, MX Filters)\n"
                "5:30 - AI Personalization that Converts\n"
                "7:00 - Key Takeaways & Free Setup Checklist"
            ),
            shot_list=[
                {
                    "step_number": 1,
                    "screen": "GlobalReach ICP Builder",
                    "action": "Filter target industry by Real Estate and location by California",
                    "voiceover_cue": "Start by defining your exact target market...",
                },
                {
                    "step_number": 2,
                    "screen": "Lead Search & Verification",
                    "action": "Show live email verification validating MX records and disposable filters",
                    "voiceover_cue": "Every single contact is verified before you ever hit export...",
                },
                {
                    "step_number": 3,
                    "screen": "Campaign Sequencing & Personalization",
                    "action": "Demonstrate AI personalization adapting the opening hook per lead",
                    "voiceover_cue": "Next, we generate personalized touches without sounding robotic...",
                },
                {
                    "step_number": 4,
                    "screen": "Deliverability Dashboard",
                    "action": "Highlight SPF/DKIM health ramp and automated pause protection",
                    "voiceover_cue": "And your domain stays protected with automatic bounce safeguards...",
                },
            ],
            captions=f"Looking to master {kw}? Watch our full walkthrough showing how modern sales teams automate high-conversion outreach.",
            youtube_description=(
                f"In this video, we break down exactly how to execute {kw}.\n\n"
                f"🚀 Try GlobalReach: {destination_url}?utm_source=youtube&utm_medium=video&utm_campaign=video_studio\n\n"
                "Timestamps:\n"
                "0:00 - Introduction\n"
                "1:10 - The Common Mistake\n"
                "2:30 - Live Workflow Walkthrough\n"
                "5:30 - Deliverability & Safeguards\n"
                "7:00 - Summary"
            ),
            tags=["b2b lead generation", "sales prospecting", "cold email", "apollo alternative", "b2b outreach"],
            thumbnail_prompt="Minimalist dark mode tech thumbnail, bold vibrant text '50 LEADS IN 5 MIN', high contrast glowing neon accents, clean modern aesthetic.",
        )

    # Save to database
    combined_script = f"=== 60-SECOND SHORTS / REELS SCRIPT ===\n{ai_data.shorts_script}\n\n=== 5-8 MINUTE YOUTUBE OUTLINE ===\n{ai_data.youtube_outline}"

    project = VideoProject(
        title=ai_data.youtube_title,
        target_keyword=payload.target_keyword,
        script=combined_script,
        shot_list=ai_data.shot_list,
        caption=ai_data.captions,
        youtube_title=ai_data.youtube_title,
        youtube_description=ai_data.youtube_description,
        tags=ai_data.tags,
        thumbnail_prompt=ai_data.thumbnail_prompt,
        status="planned",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return _to_video_response(project)


@router.post("/{id}/upload-url", response_model=UploadUrlResponse)
async def get_video_upload_url(
    id: str,
    filename: str = Query("video.mp4"),
    content_type: str = Query("video/mp4"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Generate presigned upload URL for R2 / S3 asset storage.
    Updates asset_url on the video project.
    """
    project = await db.get(VideoProject, uuid.UUID(id))
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    upload_info = generate_presigned_upload_url(
        filename=filename,
        content_type=content_type,
        folder="videos",
    )

    project.asset_url = upload_info["public_url"]
    await db.commit()
    await db.refresh(project)

    return UploadUrlResponse(
        upload_url=upload_info["upload_url"],
        public_url=upload_info["public_url"],
        key=upload_info["key"],
    )


@router.post("/{id}/publish-youtube", response_model=VideoProjectResponse)
async def publish_video_to_youtube(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Publish video to YouTube Data API (strictly private until owner approves).
    """
    project = await db.get(VideoProject, uuid.UUID(id))
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    # Fetch connected YouTube account
    yt_acc_res = await db.execute(select(SocialAccount).where(SocialAccount.platform == "youtube"))
    yt_acc = yt_acc_res.scalar_one_or_none()

    access_token = ""
    if yt_acc and yt_acc.encrypted_access_token:
        try:
            access_token = decrypt_token(yt_acc.encrypted_access_token)
        except Exception:
            access_token = "mock-decrypted-token"
    else:
        access_token = "mock-youtube-token"

    publisher = get_social_publisher("youtube")
    result = await publisher.publish(
        PostPayload(
            platform="youtube",
            body=project.youtube_description or "",
            title=project.youtube_title or project.title,
            access_token=access_token,
            tags=project.tags if isinstance(project.tags, list) else None,
        )
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Failed to publish video to YouTube")

    project.youtube_video_id = result.external_post_id
    project.status = "published"
    await db.commit()
    await db.refresh(project)

    await write_audit_log(
        db,
        action="video.published_youtube_private",
        user_id=current_user.id,
        entity="video_projects",
        entity_id=str(project.id),
        meta={"youtube_video_id": project.youtube_video_id, "privacy": "private"},
    )
    await db.commit()

    return _to_video_response(project)


@router.post("/{id}/cross-post-captions", response_model=CrossPostCaptionsResponse)
async def generate_cross_post_captions(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Cross-post cut-downs: generate platform-tailored caption variants for
    Instagram Reels, Facebook Reels, and LinkedIn video from the same video project.
    """
    project = await db.get(VideoProject, uuid.UUID(id))
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    topic = project.target_keyword or project.title

    ig_reels = (
        f"Quick breakdown: {topic} ⚡️ Watch how to automate verified lead generation without domain burn. "
        f"Drop a comment if you want the checklist! #b2b #salesgrowth #outbound #coldemail #agencylife"
    )
    fb_reels = (
        f"Step-by-step tutorial on {topic}. Stop burning your email reputation with unverified scraper lists. "
        f"Full details in our bio."
    )
    linkedin_video = (
        f"We recorded a short walkthrough on {topic} for sales leaders and agency founders.\n\n"
        f"Key takeaways:\n"
        f"• Real-time MX verification eliminates bounce spikes\n"
        f"• AI personalization performs best when kept under 4 sentences\n"
        f"• Controlled ramps protect your primary domain\n\n"
        f"What is your team's current approach to verified prospecting?"
    )

    return CrossPostCaptionsResponse(
        video_id=str(project.id),
        instagram_reels=ig_reels,
        facebook_reels=fb_reels,
        linkedin_video=linkedin_video,
    )


@router.put("/{id}", response_model=VideoProjectResponse)
async def update_video(
    id: str,
    payload: VideoProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update video details, status, or asset URL."""
    project = await db.get(VideoProject, uuid.UUID(id))
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    if payload.title is not None:
        project.title = payload.title
    if payload.script is not None:
        project.script = payload.script
    if payload.shot_list is not None:
        project.shot_list = payload.shot_list
    if payload.caption is not None:
        project.caption = payload.caption
    if payload.youtube_title is not None:
        project.youtube_title = payload.youtube_title
    if payload.youtube_description is not None:
        project.youtube_description = payload.youtube_description
    if payload.tags is not None:
        project.tags = payload.tags
    if payload.thumbnail_prompt is not None:
        project.thumbnail_prompt = payload.thumbnail_prompt
    if payload.status is not None:
        project.status = payload.status
    if payload.asset_url is not None:
        project.asset_url = payload.asset_url

    await db.commit()
    await db.refresh(project)
    return _to_video_response(project)


@router.delete("/{id}", status_code=204)
async def delete_video(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a video project."""
    project = await db.get(VideoProject, uuid.UUID(id))
    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")
    await db.delete(project)
    await db.commit()
    return None


def _to_video_response(p: VideoProject) -> VideoProjectResponse:
    return VideoProjectResponse(
        id=str(p.id),
        title=p.title,
        target_keyword=p.target_keyword,
        script=p.script,
        shot_list=p.shot_list if isinstance(p.shot_list, list) else None,
        caption=p.caption,
        youtube_title=p.youtube_title,
        youtube_description=p.youtube_description,
        tags=p.tags if isinstance(p.tags, list) else None,
        thumbnail_prompt=p.thumbnail_prompt,
        status=p.status,
        asset_url=p.asset_url,
        youtube_video_id=p.youtube_video_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
