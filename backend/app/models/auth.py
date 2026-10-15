"""Auth & Settings models: users, social_accounts, brand_profile"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # null for Google-only users
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="editor")  # owner | editor
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SocialAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "social_accounts"

    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # x|linkedin|instagram|facebook|youtube
    handle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active|expired|revoked


class BrandProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "brand_profile"

    product_name: Mapped[str] = mapped_column(String(255), nullable=False, default="GlobalReach")
    one_liner: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_props: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # list of strings
    tone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    banned_phrases: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # list of strings
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    physical_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
