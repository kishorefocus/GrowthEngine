"""Pydantic schemas for ICPs, Leads, Campaigns, Sequences, and Email Outreach endpoints."""
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ─── ICP ──────────────────────────────────────────────────────────────────────

class ICPCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    geography: Optional[str] = None
    company_size: Optional[str] = None
    titles: Optional[list[str]] = None
    keywords: Optional[list[str]] = None


class ICPUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    geography: Optional[str] = None
    company_size: Optional[str] = None
    titles: Optional[list[str]] = None
    keywords: Optional[list[str]] = None


class ICPResponse(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    geography: Optional[str] = None
    company_size: Optional[str] = None
    titles: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Lead ─────────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = "manual"
    icp_id: Optional[str] = None
    lawful_basis: Optional[str] = "legitimate_interest_b2b"


class LeadResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    verification_status: str
    icp_id: Optional[str] = None
    status: str
    lawful_basis: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadVerificationResult(BaseModel):
    id: str
    email: str
    verification_status: str
    checks: dict[str, Any]


class GlobalReachImportRequest(BaseModel):
    icp_id: str
    max_results: int = 100


class CSVColumnMapping(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None


class CSVImportRequest(BaseModel):
    icp_id: Optional[str] = None
    column_mapping: CSVColumnMapping
    rows: list[dict[str, str]]  # raw CSV rows


class ErasureRequest(BaseModel):
    reason: Optional[str] = "gdpr_erasure_request"


# ─── Suppression ──────────────────────────────────────────────────────────────

class SuppressionCreate(BaseModel):
    email_or_domain: str
    reason: Optional[str] = None


class SuppressionResponse(BaseModel):
    id: str
    email_or_domain: str
    reason: Optional[str] = None
    added_at: datetime

    class Config:
        from_attributes = True


# ─── Campaign ─────────────────────────────────────────────────────────────────

class SendingWindow(BaseModel):
    start: str  # "09:00"
    end: str    # "17:00"


class CampaignCreate(BaseModel):
    name: str
    icp_id: Optional[str] = None
    daily_limit: int = 20
    sending_window: Optional[SendingWindow] = None
    timezone_mode: str = "recipient"  # recipient | fixed


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    icp_id: Optional[str] = None
    daily_limit: Optional[int] = None
    sending_window: Optional[SendingWindow] = None
    timezone_mode: Optional[str] = None


class CampaignResponse(BaseModel):
    id: str
    name: str
    icp_id: Optional[str] = None
    status: str
    daily_limit: int
    sending_window: Optional[dict] = None
    timezone_mode: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignStats(BaseModel):
    campaign_id: str
    total_leads: int
    sent: int
    delivered: int
    opened: int
    clicked: int
    replied: int
    bounced: int
    complained: int
    bounce_rate_pct: float
    complaint_rate_pct: float
    reply_rate_pct: float


# ─── Sequence & Steps ─────────────────────────────────────────────────────────

class SequenceResponse(BaseModel):
    id: str
    campaign_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SequenceStepCreate(BaseModel):
    step_number: int = 1
    delay_days: int = 0
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    ai_personalize: bool = False


class SequenceStepUpdate(BaseModel):
    step_number: Optional[int] = None
    delay_days: Optional[int] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    ai_personalize: Optional[bool] = None


class SequenceStepResponse(BaseModel):
    id: str
    sequence_id: str
    step_number: int
    delay_days: int
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    ai_personalize: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StepStats(BaseModel):
    step_id: str
    step_number: int
    sent: int
    delivered: int
    opened: int
    clicked: int
    replied: int
    bounced: int


# ─── AI Personalization ───────────────────────────────────────────────────────

class EmailPersonalizeOutput(BaseModel):
    subject: str
    body: str


class PersonalizePreviewRequest(BaseModel):
    lead_id: str
    step_id: str


class PersonalizePreviewResponse(BaseModel):
    subject: str
    body: str
    claims_safe: bool
    violations: list[str]


# ─── Lead → Campaign ─────────────────────────────────────────────────────────

class AddLeadsToCampaignRequest(BaseModel):
    lead_ids: list[str]
    campaign_id: str


# ─── Email Messages ───────────────────────────────────────────────────────────

class EmailMessageResponse(BaseModel):
    id: str
    lead_id: str
    campaign_id: Optional[str] = None
    step_id: Optional[str] = None
    provider_message_id: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    tracking_token: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Replies / Inbox ──────────────────────────────────────────────────────────

class ReplyResponse(BaseModel):
    id: str
    message_id: str
    body: Optional[str] = None
    classification: str
    confidence: Optional[float] = None
    handled: bool
    suggested_response: Optional[str] = None
    lead: Optional[dict] = None  # basic lead info
    created_at: datetime

    class Config:
        from_attributes = True


class ReplyClassifyOutput(BaseModel):
    classification: str  # interested|not_now|not_interested|unsubscribe|out_of_office|other
    confidence: float
    suggested_response: Optional[str] = None


class ReplyHandleRequest(BaseModel):
    handled: bool = True


# ─── Domain Health ────────────────────────────────────────────────────────────

class DomainHealthResponse(BaseModel):
    domain: str
    spf: dict   # {status: pass|fail|none, record: str|None, hint: str}
    dkim: dict
    dmarc: dict
    overall: str  # pass | warn | fail
    warmup_schedule: list[dict]  # {week: int, daily_limit: int, note: str}
