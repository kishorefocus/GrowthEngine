"""
Central models __init__.py
Import all models here so Alembic and Base.metadata.create_all() can discover them.
"""
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.item import Item
from app.models.auth import User, SocialAccount, BrandProfile
from app.models.leads import ICP, Lead, SuppressionList, Campaign, Sequence, SequenceStep, EmailMessage, Reply
from app.models.social import ContentIdea, Post, VideoProject
from app.models.seo import SEOTemplate, SEOPage, ToolUsage
from app.models.launch import LaunchTask, ReviewRequest
from app.models.analytics import LinkClick, SignupAttribution, AuditLog

__all__ = [
    "Base",
    # Auth
    "User", "SocialAccount", "BrandProfile",
    # Leads
    "ICP", "Lead", "SuppressionList", "Campaign", "Sequence", "SequenceStep", "EmailMessage", "Reply",
    # Social
    "ContentIdea", "Post", "VideoProject",
    # SEO
    "SEOTemplate", "SEOPage", "ToolUsage",
    # Launch
    "LaunchTask", "ReviewRequest",
    # Analytics
    "LinkClick", "SignupAttribution", "AuditLog",
]
