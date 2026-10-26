"""
Brand profile router: GET/PUT /api/v1/brand
Every AI prompt injects this as system context for tone consistency.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import BrandProfile, User
from app.schemas.brand import BrandProfileResponse, BrandProfileUpdate

router = APIRouter(prefix="/brand", tags=["brand"])


@router.get("", response_model=BrandProfileResponse)
async def get_brand_profile(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the brand profile. Creates a default one if none exists."""
    result = await db.execute(select(BrandProfile).limit(1))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = BrandProfile(
            product_name="GetyourclientsB2B",
            website_url="https://www.getyourclientsb2b.com",
            one_liner="B2B client discovery & cold outreach CRM across 190+ countries",
            value_props=["Interactive global map discovery", "Verified B2B emails & contacts", "Cold outreach CRM & automated sequences"],
            tone="professional, direct, honest",
            banned_phrases=[],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


@router.put("", response_model=BrandProfileResponse)
async def update_brand_profile(
    payload: BrandProfileUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update the brand profile. Only set fields are changed (PATCH semantics)."""
    result = await db.execute(select(BrandProfile).limit(1))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = BrandProfile()
        db.add(profile)

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile
