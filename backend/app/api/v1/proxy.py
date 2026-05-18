import time
import json
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.services.key_service import get_api_key_by_raw, check_rate_limit, check_daily_token_limit
from app.services.proxy_service import proxy_request, proxy_stream, extract_usage_from_response
from app.services.usage_service import record_usage

router = APIRouter(tags=["Proxy"])

# Redis key for caching provider settings
# Redis key for caching provider settings
PROVIDER_CACHE_TTL = 300  # 5 minutes
logger = logging.getLogger("Proxy")


async def _get_provider_settings(provider_id: uuid.UUID | None, db: AsyncSession) -> tuple[str | None, str | None]:
    """Return (base_url, api_key) for the given provider, using Redis cache."""
    if provider_id is None:
        return None, None

    redis = await get_redis()
    cache_key = f"provider:{provider_id}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return data["base_url"], data["api_key"]

    # Fetch from DB
    from app.models.provider import Provider
    res = await db.execute(select(Provider).where(Provider.id == provider_id, Provider.is_enabled == True))
    provider = res.scalar_one_or_none()
    if not provider:
        return None, None

    await redis.setex(cache_key, PROVIDER_CACHE_TTL, json.dumps({
        "base_url": provider.base_url,
        "api_key": provider.api_key,
    }))
    return provider.base_url, provider.api_key


async def _validate_api_key(request: Request, db: AsyncSession):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use: Bearer sk-...",
        )
    raw_key = auth_header[len("Bearer "):]
    api_key = await get_api_key_by_raw(db, raw_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    if not await check_rate_limit(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in a minute.",
        )

    if not await check_daily_token_limit(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily token limit exceeded.",
        )

    return api_key


@router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_openai(
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Proxy all OpenAI API requests. Requires a valid API key in Authorization header."""
    client_ip = request.client.host if request.client else "Unknown IP"
    logger.info(f"[Req ] <{client_ip}> {request.method} /{path}")

    api_key = await _validate_api_key(request, db)

    # Resolve provider settings (base_url + upstream api_key)
    base_url, upstream_key = await _get_provider_settings(api_key.provider_id, db)

    body = await request.body()
    headers = dict(request.headers)
    method = request.method

    is_stream = False
    try:
        body_json = json.loads(body) if body else {}
        is_stream = body_json.get("stream", False)
        requested_model = body_json.get("model")

        # Enforce allowed models if list is not empty
        if api_key.allowed_models and requested_model:
            if requested_model not in api_key.allowed_models:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key is not authorized for model '{requested_model}'. Allowed: {api_key.allowed_models}"
                )
    except json.JSONDecodeError:
        body_json = {}

    query_string = request.url.query
    full_path = f"v1/{path}"
    if query_string:
        full_path += f"?{query_string}"

    if is_stream:
        stream_gen, start_time = await proxy_stream(
            path=full_path,
            method=method,
            headers=headers,
            body=body,
            base_url=base_url,
            upstream_api_key=upstream_key,
        )

        async def event_stream():
            async for chunk in stream_gen:
                yield chunk

        await record_usage(
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            model=body_json.get("model", "unknown"),
            endpoint=f"v1/{path}",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=None,
            status_code=200,
        )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        response, latency_ms = await proxy_request(
            path=full_path,
            method=method,
            headers=headers,
            body=body,
            base_url=base_url,
            upstream_api_key=upstream_key,
        )

        usage = extract_usage_from_response(response.content)
        await record_usage(
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            model=usage["model"],
            endpoint=f"v1/{path}",
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            latency_ms=latency_ms,
            status_code=response.status_code,
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type", "application/json"),
        )
