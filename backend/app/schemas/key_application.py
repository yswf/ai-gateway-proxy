import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, field_validator


class KeyApplicationCreate(BaseModel):
    provider_id: uuid.UUID
    requested_models: list[str] = []
    reason: str
    intended_use: Optional[str] = None


class KeyApplicationReview(BaseModel):
    """Admin review action."""
    status: str  # "approved" or "rejected"
    admin_note: Optional[str] = None
    rate_limit_rpm: int = 60
    token_limit_daily: int = 0
    expires_at: Optional[datetime] = None

    @field_validator("expires_at")
    @classmethod
    def make_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


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
