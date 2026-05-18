import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.models.api_key import APIKey
from app.models.usage_log import UsageLog
from app.core.database import AsyncSessionLocal
from app.services.key_service import increment_daily_tokens


async def record_usage(
    api_key_id: uuid.UUID,
    user_id: uuid.UUID,
    model: str,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int | None,
    status_code: int,
):
    """Fire-and-forget usage recording — runs in a background task."""
    asyncio.create_task(
        _write_usage_log(
            api_key_id=api_key_id,
            user_id=user_id,
            model=model,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status_code=status_code,
        )
    )


async def _write_usage_log(
    api_key_id: uuid.UUID,
    user_id: uuid.UUID,
    model: str,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int | None,
    status_code: int,
):
    try:
        async with AsyncSessionLocal() as db:
            log = UsageLog(
                api_key_id=api_key_id,
                user_id=user_id,
                model=model,
                endpoint=endpoint,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status_code=status_code,
            )
            db.add(log)

            # Update cumulative totals on the APIKey row
            await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    total_tokens_used=APIKey.total_tokens_used + total_tokens,
                    last_used_at=datetime.utcnow(),
                )
            )
            await db.commit()

        # Update Redis daily counter
        if total_tokens > 0:
            await increment_daily_tokens(api_key_id, total_tokens)

    except Exception as exc:
        # Log but don't propagate — this is a background task
        print(f"[usage_service] Failed to record usage: {exc}")
