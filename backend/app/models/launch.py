"""Launch & Reviews models: launch_tasks, review_requests"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LaunchTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "launch_tasks"

    platform: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # product_hunt|g2|capterra|reddit|indiehackers|other
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|in_progress|done
    assets: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class ReviewRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_requests"

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # g2|capterra|other
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|sent|reviewed
