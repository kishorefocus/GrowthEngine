"""
Pydantic schemas for Launch Hub and Reviews.
"""
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class LaunchTaskCreate(BaseModel):
    platform: str = Field(..., description="product_hunt | g2 | capterra | reddit | indiehackers | other")
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = Field(default="pending", description="pending | in_progress | done")
    assets: Optional[dict[str, Any]] = None


class LaunchTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    assets: Optional[dict[str, Any]] = None


class LaunchTaskResponse(BaseModel):
    id: uuid.UUID
    platform: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    assets: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LaunchAssetGenerateRequest(BaseModel):
    platform: str
    task_type: str = Field(..., description="e.g. tagline, maker_comment, checklist, listing_copy, reddit_journey, ih_milestone")
    custom_notes: Optional[str] = None


class ReviewRequestCreate(BaseModel):
    user_email: EmailStr
    platform: str = Field(default="g2", description="g2 | capterra")


class ReviewRequestResponse(BaseModel):
    id: uuid.UUID
    user_email: str
    platform: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
