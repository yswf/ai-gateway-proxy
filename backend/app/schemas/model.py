import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ModelCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    is_enabled: bool = True
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    sort_order: int = 0
    provider_id: Optional[uuid.UUID] = None


class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    sort_order: Optional[int] = None
    provider_id: Optional[uuid.UUID] = None


class ModelResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_enabled: bool
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    provider_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    total: int
    items: list[ModelResponse]
