"""Social & Video models: content_ideas, posts, video_projects"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ContentIdea(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "content_ideas"

    topic: Mapped[str] = mapped_column(Text, nullable=False)
    pillar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # ai|manual|seo_gap
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|approved|archived


class Post(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "posts"

    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("content_ideas.id", ondelete="SET NULL"), nullable=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # x|linkedin|instagram|facebook|youtube
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_urls: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # list of URLs
    link_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft|pending_approval|approved|scheduled|published|failed|rejected
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    external_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class VideoProject(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "video_projects"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    target_keyword: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shot_list: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    youtube_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    thumbnail_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    asset_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
