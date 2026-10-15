from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    title: str = Field(..., max_length=120, example="GrowthEngine Test Task")
    description: str | None = Field(None, max_length=255, example="Testing PostgreSQL connection")


class ItemCreate(ItemBase):
    pass


class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
