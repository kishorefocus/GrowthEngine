"""Analytics models: link_clicks, signup_attributions, audit_log"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LinkClick(UUIDMixin, TimestampMixin, Base):
    """Records every short-link click with UTM data and visitor ID."""
    __tablename__ = "link_clicks"

    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    visitor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    short_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    destination_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    landed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignupAttribution(UUIDMixin, TimestampMixin, Base):
    """Multi-touch attribution for signups. Populated by HMAC-signed webhook."""
    __tablename__ = "signup_attributions"

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_touch: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # UTM + visitor_id
    last_touch: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    signed_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """Immutable audit trail for approvals, sends, and deletions."""
    __tablename__ = "audit_log"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g. "post.approved", "email.sent"
    entity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)     # e.g. "posts", "email_messages"
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)   # UUID as string for flexibility
    meta: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
