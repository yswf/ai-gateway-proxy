import uuid
from pydantic import BaseModel
from typing import Optional


class DailyUsage(BaseModel):
    date: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_count: int


class ModelUsage(BaseModel):
    model: str
    total_tokens: int
    request_count: int


class KeyUsageSummary(BaseModel):
    key_id: str
    key_prefix: str
    key_name: str
    total_tokens: int
    request_count: int


class UserStatsSummary(BaseModel):
    total_tokens_used: int
    total_requests: int
    active_keys: int
    total_keys: int
    today_tokens: int
    today_requests: int

class UserTokenRankingItem(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str | None = None
    total_tokens: int
    request_count: int

class UserTokenRankingResponse(BaseModel):
    items: list[UserTokenRankingItem]


class AdminStatsSummary(BaseModel):
    total_users: int
    total_keys: int
    active_keys: int
    total_tokens_all_time: int
    total_requests_all_time: int
    today_tokens: int
    today_requests: int


class UsageLogItem(BaseModel):
    id: int
    model: str
    endpoint: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: Optional[int]
    status_code: int
    created_at: str


class UsageLogListResponse(BaseModel):
    total: int
    items: list[UsageLogItem]
