"""
Pydantic schemas for Public Free Lead-Magnet Tools.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class SubjectGradeRequest(BaseModel):
    subject_line: str = Field(..., min_length=3, max_length=200)
    industry_context: Optional[str] = Field(None, max_length=100)
    email_captured: Optional[str] = Field(None, max_length=255)
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class SubjectRewrite(BaseModel):
    style: str
    subject: str
    why_it_works: str


class SubjectGradeResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    reasons: list[str]
    rewrites: list[SubjectRewrite]
    input_stats: dict[str, Any]
    cta: dict[str, str]


class EmailVerifyToolRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    email_captured: Optional[str] = Field(None, description="Email captured from user to unlock more than 5 checks")
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class EmailVerifyToolResponse(BaseModel):
    email: str
    syntax_ok: bool
    mx_ok: bool
    is_disposable: bool
    is_role: bool
    status: str
    notes: list[str]
    daily_checks_remaining: int
    requires_email_unlock: bool
    cta: dict[str, str]
