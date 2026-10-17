"""
Pydantic schemas for Programmatic SEO and Templates.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SEOTemplateCreate(BaseModel):
    type: str = Field(..., description="industry_city | alternative | use_case")
    url_pattern: str = Field(..., description="e.g. /find-leads/{industry}/{city} or /alternatives/{competitor}/{niche}")
    title_pattern: str = Field(..., description="e.g. Find {industry} Leads in {city} | GlobalReach")
    h1_pattern: str = Field(..., description="e.g. Find Verified {industry} Leads in {city}")
    body_prompt: str = Field(..., description="Custom prompt directives for Claude")


class SEOTemplateResponse(SEOTemplateCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SEOGenerateRequest(BaseModel):
    template_id: uuid.UUID
    variables_list: list[dict[str, Any]] = Field(default_factory=list, description="Array of variable dictionaries")
    csv_content: Optional[str] = Field(None, description="Optional raw CSV string containing variable columns")


class SEOPageResponse(BaseModel):
    id: uuid.UUID
    template_id: Optional[uuid.UUID] = None
    slug: str
    variables: Optional[dict[str, Any]] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    content_json: Optional[dict[str, Any]] = None
    status: str
    published_at: Optional[datetime] = None
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SEOPageBatchPublishRequest(BaseModel):
    page_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100, description="List of page IDs to approve and publish")


class SEOPublicPageResponse(BaseModel):
    slug: str
    title: str
    meta_description: str
    content_json: dict[str, Any]
    schema_org: dict[str, Any]
    published_at: Optional[datetime] = None
