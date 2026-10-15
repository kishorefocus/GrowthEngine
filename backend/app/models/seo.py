"""SEO & Tools models: seo_templates, seo_pages, tool_usages"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SEOTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "seo_templates"

    type: Mapped[str] = mapped_column(String(30), nullable=False)  # industry_city|alternative|use_case
    url_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    title_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    h1_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    body_prompt: Mapped[str] = mapped_column(Text, nullable=False)


class SEOPage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "seo_pages"

    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("seo_templates.id", ondelete="SET NULL"), nullable=True)
    slug: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    variables: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|published
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class ToolUsage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tool_usages"

    tool_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email_captured: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
