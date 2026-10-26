"""Pydantic schemas for Social & Video studio: connections, ideas, posts, calendar, videos."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Connections (OAuth) ──────────────────────────────────────────────────────

class SocialAccountResponse(BaseModel):
    id: str
    platform: str
    handle: Optional[str] = None
    external_id: Optional[str] = None
    status: str  # active | expired | revoked
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OAuthAuthorizeResponse(BaseModel):
    platform: str
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class DirectConnectRequest(BaseModel):
    platform: str
    handle: Optional[str] = None
    external_id: Optional[str] = None
    access_token: str


# ─── Content Ideas ────────────────────────────────────────────────────────────

class IdeaCreate(BaseModel):
    topic: str
    pillar: Optional[str] = None
    source: str = "manual"  # ai | manual | seo_gap
    status: str = "draft"   # draft | approved | archived


class IdeaUpdate(BaseModel):
    topic: Optional[str] = None
    pillar: Optional[str] = None
    status: Optional[str] = None


class IdeaResponse(BaseModel):
    id: str
    topic: str
    pillar: Optional[str] = None
    source: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateIdeasRequest(BaseModel):
    count: int = 20
    pillars: Optional[list[str]] = None
    custom_prompt: Optional[str] = None


class GenerateIdeasResponse(BaseModel):
    generated_count: int
    ideas: list[IdeaResponse]


# ─── Posts ────────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    idea_id: Optional[str] = None
    platform: str  # x | linkedin | instagram | facebook | youtube
    body: str
    media_urls: Optional[list[str]] = None
    link_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: str = "draft"


class PostUpdate(BaseModel):
    body: Optional[str] = None
    media_urls: Optional[list[str]] = None
    link_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None


class PostResponse(BaseModel):
    id: str
    idea_id: Optional[str] = None
    platform: str
    body: Optional[str] = None
    media_urls: Optional[list[str]] = None
    link_url: Optional[str] = None
    utm: Optional[dict[str, Any]] = None
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GeneratePostsRequest(BaseModel):
    idea_id: str
    platforms: Optional[list[str]] = None  # ["x", "linkedin", "instagram", "facebook"]
    link_url: Optional[str] = None
    schedule_start: Optional[datetime] = None


class GeneratePostsResponse(BaseModel):
    idea_id: str
    posts: list[PostResponse]


class ApprovePostRequest(BaseModel):
    scheduled_at: Optional[datetime] = None


class ReschedulePostRequest(BaseModel):
    scheduled_at: datetime


class RejectPostRequest(BaseModel):
    reason: Optional[str] = None


# ─── Calendar Feed ────────────────────────────────────────────────────────────

class CalendarItem(BaseModel):
    id: str
    type: str = "post"  # post | task
    platform: str
    title: str
    body: str
    status: str
    scheduled_at: datetime
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    error: Optional[str] = None


class CalendarFeedResponse(BaseModel):
    items: list[CalendarItem]
    best_time_suggestions: dict[str, list[str]]  # platform -> ["09:00", "13:00", "17:00"]


# ─── Video Studio ─────────────────────────────────────────────────────────────

class VideoPlanRequest(BaseModel):
    target_keyword: str
    additional_notes: Optional[str] = None


class VideoProjectResponse(BaseModel):
    id: str
    title: str
    target_keyword: Optional[str] = None
    script: Optional[str] = None
    shot_list: Optional[list[dict[str, Any]]] = None
    caption: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_description: Optional[str] = None
    tags: Optional[list[str]] = None
    thumbnail_prompt: Optional[str] = None
    status: str  # draft | planned | recorded | published
    asset_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    cross_post_captions: Optional[dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    script: Optional[str] = None
    shot_list: Optional[list[dict[str, Any]]] = None
    caption: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_description: Optional[str] = None
    tags: Optional[list[str]] = None
    thumbnail_prompt: Optional[str] = None
    status: Optional[str] = None
    asset_url: Optional[str] = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    public_url: str
    key: str
