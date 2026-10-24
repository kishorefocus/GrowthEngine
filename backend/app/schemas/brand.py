"""Pydantic schemas for brand profile."""
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, HttpUrl


class BrandProfileUpdate(BaseModel):
    product_name: Optional[str] = None
    one_liner: Optional[str] = None
    value_props: Optional[list[str]] = None
    tone: Optional[str] = None
    banned_phrases: Optional[list[str]] = None
    website_url: Optional[str] = None
    physical_address: Optional[str] = None


class BrandProfileResponse(BaseModel):
    id: Union[UUID, str]
    product_name: str
    one_liner: Optional[str]
    value_props: Optional[list]
    tone: Optional[str]
    banned_phrases: Optional[list]
    website_url: Optional[str]
    physical_address: Optional[str]

    class Config:
        from_attributes = True
