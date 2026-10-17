"""Leads & Outreach models: icps, leads, suppression_list, campaigns, sequences, email_messages, replies"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ICP(UUIDMixin, TimestampMixin, Base):
    """Ideal Customer Profile"""
    __tablename__ = "icps"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    geography: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    titles: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)    # list of job titles
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # list of keywords


class Lead(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified")
    icp_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new"
    )  # new|queued|contacted|replied|signed_up|bounced|unsubscribed
    lawful_basis: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="legitimate_interest_b2b")
    # GDPR: lawful basis for processing. "legitimate_interest_b2b" for B2B cold outreach.


class SuppressionList(UUIDMixin, TimestampMixin, Base):
    """Email or domain suppression. Checked before every send."""
    __tablename__ = "suppression_list"

    email_or_domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Campaign(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icp_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("icps.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|active|paused|completed
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    sending_window: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"start": "09:00", "end": "17:00"}
    timezone_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="recipient")  # recipient|fixed


class Sequence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sequences"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)


class SequenceStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sequence_steps"

    sequence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subject_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_personalize: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class EmailMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "email_messages"

    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sequence_steps.id", ondelete="SET NULL"), nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled"
    )  # scheduled|sent|delivered|opened|clicked|replied|bounced|complained
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)


class Reply(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "replies"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(
        String(30), nullable=False, default="other"
    )  # interested|not_now|not_interested|unsubscribe|out_of_office|other
    confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    suggested_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
