"""
Content ideas router:
- POST /ideas/generate: generates 20 ideas across 5 core pillars via AI
- CRUD for content_ideas: list, create, update, delete
- Convert idea to platform drafts
"""
import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import BrandProfile, User
from app.models.social import ContentIdea
from app.schemas.social import (
    GenerateIdeasRequest,
    GenerateIdeasResponse,
    IdeaCreate,
    IdeaResponse,
    IdeaUpdate,
)
from app.services.ai import generate, _load_prompt
from app.services.claims_guard import check_claims

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ideas", tags=["ideas"])

PILLARS = [
    "how-to",
    "build-in-public",
    "competitor_alternatives",
    "industry_lead_lists",
    "tips_and_stats",
]

DEFAULT_FALLBACK_IDEAS = [
    {"topic": "How to build a verified 500-lead list for commercial roofing agencies in 15 minutes with GetyourclientsB2B", "pillar": "how-to"},
    {"topic": "We filtered 100,000 cold emails: here are the 4 phrases that trigger spam filters instantly", "pillar": "tips_and_stats"},
    {"topic": "Apollo.io vs GetyourclientsB2B: Why real-time MX validation beats cached scraper databases", "pillar": "competitor_alternatives"},
    {"topic": "Building our email deliverability ramp in public: from 20 to 500 daily emails with 0% domain burn", "pillar": "build-in-public"},
    {"topic": "50 high-growth B2B fintech startups in London hiring VP Sales right now", "pillar": "industry_lead_lists"},
    {"topic": "The 3-line follow-up email that achieved a 22% reply rate without being pushy", "pillar": "how-to"},
    {"topic": "Why buying aged domains is killing your outbound and what we did instead at GetyourclientsB2B", "pillar": "build-in-public"},
    {"topic": "ZoomInfo alternative for boutique recruitment agencies on a budget: GetyourclientsB2B", "pillar": "competitor_alternatives"},
    {"topic": "Cold email benchmarks in 2026: open rates, click-throughs, and realistic conversion expectations", "pillar": "tips_and_stats"},
    {"topic": "Top 40 real estate development firms in Austin with verified founder contacts on GetyourclientsB2B", "pillar": "industry_lead_lists"},
    {"topic": "Step-by-step tutorial: Setting up SPF, DKIM, and DMARC for a dedicated outreach subdomain", "pillar": "how-to"},
    {"topic": "How we automated prospect reply classification into 6 categories with AI inside GetyourclientsB2B", "pillar": "build-in-public"},
    {"topic": "Lusha vs GetyourclientsB2B: Cost comparison and email accuracy breakdown", "pillar": "competitor_alternatives"},
    {"topic": "The subtle difference between a personalized hook and creepy surveillance in sales emails", "pillar": "tips_and_stats"},
    {"topic": "30 fast-growing cybersecurity companies looking for channel partners this quarter", "pillar": "industry_lead_lists"},
    {"topic": "How to convert an interested cold reply into a booked calendar discovery call with GetyourclientsB2B", "pillar": "how-to"},
    {"topic": "Our worst outreach campaign ever: 3 fatal mistakes we will never repeat", "pillar": "build-in-public"},
    {"topic": "Hunter.io alternative with built-in multi-step campaign sequences: GetyourclientsB2B", "pillar": "competitor_alternatives"},
    {"topic": "Deliverability metrics you must track weekly: bounce rates, complaints, and spam trap signals", "pillar": "tips_and_stats"},
    {"topic": "Top 50 Shopify Plus agencies in North America with key decision makers via GetyourclientsB2B", "pillar": "industry_lead_lists"},
]


class _AIIdeaItem(BaseModel):
    topic: str
    pillar: str
    suggested_angle: Optional[str] = None


class _AIIdeasSchema(BaseModel):
    ideas: list[_AIIdeaItem]


@router.get("", response_model=list[IdeaResponse])
async def list_ideas(
    pillar: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List content ideas with optional filters."""
    query = select(ContentIdea).order_by(desc(ContentIdea.created_at))
    if pillar:
        query = query.where(ContentIdea.pillar == pillar)
    if status_filter:
        query = query.where(ContentIdea.status == status_filter)
    if source:
        query = query.where(ContentIdea.source == source)

    result = await db.execute(query)
    ideas = result.scalars().all()
    return [
        IdeaResponse(
            id=str(i.id),
            topic=i.topic,
            pillar=i.pillar,
            source=i.source,
            status=i.status,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in ideas
    ]


@router.post("", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_idea(
    payload: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Manually add a content idea."""
    check_claims(payload.topic)
    idea = ContentIdea(
        topic=payload.topic,
        pillar=payload.pillar,
        source=payload.source,
        status=payload.status,
    )
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    return IdeaResponse(
        id=str(idea.id),
        topic=idea.topic,
        pillar=idea.pillar,
        source=idea.source,
        status=idea.status,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )


@router.post("/generate", response_model=GenerateIdeasResponse)
async def generate_ideas(
    payload: GenerateIdeasRequest = GenerateIdeasRequest(),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Generate 20 ideas across 5 pillars:
    - how-to lead-gen tutorials
    - build-in-public
    - competitor alternatives
    - industry lead lists
    - tips and stats
    """
    # Fetch brand context
    brand_res = await db.execute(select(BrandProfile).limit(1))
    brand = brand_res.scalar_one_or_none()
    brand_context = {
        "product_name": brand.product_name if brand else "GetyourclientsB2B",
        "one_liner": brand.one_liner if brand else "B2B client discovery & cold outreach CRM across 190+ countries",
        "tone": brand.tone if brand else "Direct, authoritative, tactical, transparent",
        "value_props": brand.value_props if brand else ["Interactive global map discovery", "Verified B2B emails & contacts", "Cold outreach CRM & automated sequences"],
    }

    generated_items: list[dict] = []

    if settings.anthropic_api_key:
        try:
            template = _load_prompt("social_ideas")
            rendered_prompt = template.format(**brand_context)
            if payload.custom_prompt:
                rendered_prompt += f"\nSpecific focus for this batch: {payload.custom_prompt}"

            ai_result = await generate(
                prompt=rendered_prompt,
                response_model=_AIIdeasSchema,
                brand_context=brand_context,
                max_tokens=3000,
            )
            for item in ai_result.ideas:
                generated_items.append({"topic": item.topic, "pillar": item.pillar, "source": "ai"})
        except Exception as exc:
            logger.warning("AI generation of ideas failed (%s), using curated defaults", exc)

    if not generated_items:
        # Curated high-converting default list
        for item in DEFAULT_FALLBACK_IDEAS[: payload.count]:
            generated_items.append({**item, "source": "ai"})

    # Save ideas into database
    created_ideas: list[ContentIdea] = []
    for item in generated_items:
        check_claims(item["topic"])
        idea = ContentIdea(
            topic=item["topic"],
            pillar=item["pillar"],
            source=item.get("source", "ai"),
            status="draft",
        )
        db.add(idea)
        created_ideas.append(idea)

    await db.commit()
    for idea in created_ideas:
        await db.refresh(idea)

    return GenerateIdeasResponse(
        generated_count=len(created_ideas),
        ideas=[
            IdeaResponse(
                id=str(i.id),
                topic=i.topic,
                pillar=i.pillar,
                source=i.source,
                status=i.status,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in created_ideas
        ],
    )


@router.put("/{id}", response_model=IdeaResponse)
async def update_idea(
    id: str,
    payload: IdeaUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update an idea's topic, pillar, or status."""
    idea_uuid = uuid.UUID(id)
    idea = await db.get(ContentIdea, idea_uuid)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if payload.topic is not None:
        check_claims(payload.topic)
        idea.topic = payload.topic
    if payload.pillar is not None:
        idea.pillar = payload.pillar
    if payload.status is not None:
        idea.status = payload.status

    await db.commit()
    await db.refresh(idea)
    return IdeaResponse(
        id=str(idea.id),
        topic=idea.topic,
        pillar=idea.pillar,
        source=idea.source,
        status=idea.status,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )


@router.delete("/{id}", status_code=204)
async def delete_idea(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a content idea."""
    idea_uuid = uuid.UUID(id)
    idea = await db.get(ContentIdea, idea_uuid)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await db.delete(idea)
    await db.commit()
    return None
