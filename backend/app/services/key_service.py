import secrets
import hashlib
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyCreatedResponse
from app.core.redis_client import get_redis
import json


KEY_PREFIX = "sk-"
KEY_BYTES = 32


def generate_raw_key() -> str:
    """Generate a random API key like sk-<64 hex chars>."""
    return KEY_PREFIX + secrets.token_hex(KEY_BYTES)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    """Return first 12 chars for display: sk-AbCd1234..."""
    return raw_key[:12]


async def create_api_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: APIKeyCreate,
    provider_id: uuid.UUID | None = None,
) -> APIKeyCreatedResponse:
    raw_key = generate_raw_key()
    key_hash = hash_key(raw_key)
    key_prefix = get_key_prefix(raw_key)

    api_key = APIKey(
        user_id=user_id,
        provider_id=provider_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=data.name,
        plaintext_key=raw_key,
        rate_limit_rpm=data.rate_limit_rpm,
        token_limit_daily=data.token_limit_daily,
        expires_at=data.expires_at,
        allowed_models=data.allowed_models,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        user_id=api_key.user_id,
        provider_id=api_key.provider_id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        plaintext_key=api_key.plaintext_key,
        status=api_key.status,
        rate_limit_rpm=api_key.rate_limit_rpm,
        token_limit_daily=api_key.token_limit_daily,
        total_tokens_used=api_key.total_tokens_used,
        allowed_models=api_key.allowed_models or [],
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        full_key=raw_key,
    )


async def get_api_key_by_raw(db: AsyncSession, raw_key: str) -> APIKey | None:
    """Validate a raw API key from request headers, using Redis cache."""
    key_hash = hash_key(raw_key)

    # Try Redis cache first
    redis = await get_redis()
    cache_key = f"apikey:{key_hash}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        if data.get("status") != "active":
            return None
        # Return a lightweight object from cache
        return APIKey(
            id=uuid.UUID(data["id"]),
            user_id=uuid.UUID(data["user_id"]),
            provider_id=uuid.UUID(data["provider_id"]) if data.get("provider_id") else None,
            status=data["status"],
            rate_limit_rpm=data["rate_limit_rpm"],
            token_limit_daily=data["token_limit_daily"],
            allowed_models=data.get("allowed_models", []),
        )

    # Fall back to DB
    key_obj = await _get_key_from_db(db, key_hash)
    if key_obj:
        # Cache for 5 minutes
        cache_data = {
            "id": str(key_obj.id),
            "user_id": str(key_obj.user_id),
            "provider_id": str(key_obj.provider_id) if key_obj.provider_id else None,
            "status": key_obj.status,
            "rate_limit_rpm": key_obj.rate_limit_rpm,
            "token_limit_daily": key_obj.token_limit_daily,
            "allowed_models": key_obj.allowed_models,
        }
        await redis.setex(cache_key, 300, json.dumps(cache_data))
    return key_obj


async def _get_key_from_db(db: AsyncSession, key_hash: str) -> APIKey | None:
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.status == "active",
        )
    )
    key_obj = result.scalar_one_or_none()
    if key_obj:
        # Check expiry
        if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
            return None
    return key_obj


async def invalidate_key_cache(key_hash: str):
    redis = await get_redis()
    await redis.delete(f"apikey:{key_hash}")


async def check_rate_limit(api_key: APIKey) -> bool:
    """Returns True if within rate limit, False if exceeded."""
    if api_key.rate_limit_rpm == 0:
        return True
    redis = await get_redis()
    now = datetime.utcnow()
    window_key = f"ratelimit:{api_key.id}:{now.strftime('%Y%m%d%H%M')}"
    count = await redis.incr(window_key)
    if count == 1:
        await redis.expire(window_key, 60)
    return count <= api_key.rate_limit_rpm


async def check_daily_token_limit(api_key: APIKey) -> bool:
    """Returns True if within daily token limit."""
    if api_key.token_limit_daily == 0:
        return True
    redis = await get_redis()
    today = datetime.utcnow().strftime("%Y%m%d")
    daily_key = f"daily_tokens:{api_key.id}:{today}"
    used = await redis.get(daily_key)
    used_count = int(used) if used else 0
    return used_count < api_key.token_limit_daily


async def increment_daily_tokens(api_key_id: uuid.UUID, tokens: int):
    redis = await get_redis()
    today = datetime.utcnow().strftime("%Y%m%d")
    daily_key = f"daily_tokens:{api_key_id}:{today}"
    await redis.incrby(daily_key, tokens)
    # Set TTL to 2 days so it auto-expires
    await redis.expire(daily_key, 172800)
