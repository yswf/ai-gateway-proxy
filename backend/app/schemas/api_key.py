import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from typing import Optional


class APIKeyCreate(BaseModel):
    name: str
    rate_limit_rpm: int = 60
    token_limit_daily: int = 0  # 0 = unlimited
    expires_at: Optional[datetime] = None
    allowed_models: list[str] = []

    @field_validator("expires_at")
    @classmethod
    def make_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    token_limit_daily: Optional[int] = None
    expires_at: Optional[datetime] = None
    allowed_models: Optional[list[str]] = None

    @field_validator("expires_at")
    @classmethod
    def make_naive_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_id: Optional[uuid.UUID] = None
    key_prefix: str
    name: str
    plaintext_key: Optional[str] = None
    status: str
    rate_limit_rpm: int
    token_limit_daily: int
    total_tokens_used: int
    allowed_models: list[str] = []
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(APIKeyResponse):
    """Returned only once on creation, includes the full plaintext key."""
    full_key: str


class APIKeyListResponse(BaseModel):
    total: int
    items: list[APIKeyResponse]
