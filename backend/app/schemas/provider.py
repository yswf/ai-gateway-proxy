import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator


class ProviderCreate(BaseModel):
    name: str
    display_name: str
    base_url: str
    api_key: str
    description: Optional[str] = None
    is_enabled: bool = True
    sort_order: int = 0

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: Optional[str]) -> Optional[str]:
        return v.rstrip("/") if v else v


class ProviderResponse(BaseModel):
    """Full response including api_key — admin only."""
    id: uuid.UUID
    name: str
    display_name: str
    base_url: str
    api_key: str
    description: Optional[str] = None
    is_enabled: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderPublic(BaseModel):
    """Public response without api_key — for non-admin users."""
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_enabled: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ProviderListResponse(BaseModel):
    total: int
    items: list[ProviderResponse]


class ProviderPublicListResponse(BaseModel):
    total: int
    items: list[ProviderPublic]


class SyncedModel(BaseModel):
    """A model returned from a provider's /v1/models endpoint."""
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None
