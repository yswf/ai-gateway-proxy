import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class KeyApplicationCreate(BaseModel):
    provider_id: uuid.UUID
    requested_models: list[str] = []
    reason: str
    intended_use: Optional[str] = None


class KeyApplicationReview(BaseModel):
    """Admin review action."""
    status: str  # "approved" or "rejected"
    admin_note: Optional[str] = None


class KeyApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_id: uuid.UUID
    requested_models: list[str] = []
    reason: str
    intended_use: Optional[str] = None
    status: str
    admin_note: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    api_key_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Joined fields
    provider_name: Optional[str] = None
    provider_display_name: Optional[str] = None
    user_email: Optional[str] = None
    user_display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class KeyApplicationListResponse(BaseModel):
    total: int
    items: list[KeyApplicationResponse]
