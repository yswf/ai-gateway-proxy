import uuid
from typing import Annotated, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.usage_log import UsageLog
from app.models.api_key import APIKey
from app.schemas.stats import (
    DailyUsage,
    ModelUsage,
    KeyUsageSummary,
    UserStatsSummary,
    UsageLogListResponse,
    UsageLogItem,
)
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/summary", response_model=UserStatsSummary)
async def get_my_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Total usage
    total_res = await db.execute(
        select(
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.count(UsageLog.id),
        ).where(UsageLog.user_id == current_user.id)
    )
    total_tokens, total_requests = total_res.one()

    # Today usage
    today_res = await db.execute(
        select(
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.count(UsageLog.id),
        ).where(
            UsageLog.user_id == current_user.id,
            UsageLog.created_at >= today_start,
        )
    )
    today_tokens, today_requests = today_res.one()

    # Keys
    keys_res = await db.execute(
        select(
            func.count(APIKey.id),
            func.count(APIKey.id).filter(APIKey.status == "active"),
        ).where(APIKey.user_id == current_user.id)
    )
    total_keys, active_keys = keys_res.one()

    return UserStatsSummary(
        total_tokens_used=total_tokens,
        total_requests=total_requests,
        active_keys=active_keys,
        total_keys=total_keys,
        today_tokens=today_tokens,
        today_requests=today_requests,
    )


@router.get("/daily", response_model=list[DailyUsage])
async def get_daily_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=90),
):
    start_date = datetime.utcnow() - timedelta(days=days)
    res = await db.execute(
        select(
            func.date(UsageLog.created_at).label("date"),
            func.coalesce(func.sum(UsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(UsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(UsageLog.total_tokens), 0).label("total_tokens"),
            func.count(UsageLog.id).label("request_count"),
        )
        .where(
            UsageLog.user_id == current_user.id,
            UsageLog.created_at >= start_date,
        )
        .group_by(func.date(UsageLog.created_at))
        .order_by(func.date(UsageLog.created_at))
    )
    rows = res.all()
    return [
        DailyUsage(
            date=str(row.date),
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            total_tokens=row.total_tokens,
            request_count=row.request_count,
        )
        for row in rows
    ]


@router.get("/models", response_model=list[ModelUsage])
async def get_model_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=90),
):
    start_date = datetime.utcnow() - timedelta(days=days)
    res = await db.execute(
        select(
            UsageLog.model,
            func.coalesce(func.sum(UsageLog.total_tokens), 0).label("total_tokens"),
            func.count(UsageLog.id).label("request_count"),
        )
        .where(
            UsageLog.user_id == current_user.id,
            UsageLog.created_at >= start_date,
        )
        .group_by(UsageLog.model)
        .order_by(func.sum(UsageLog.total_tokens).desc())
    )
    rows = res.all()
    return [
        ModelUsage(model=row.model, total_tokens=row.total_tokens, request_count=row.request_count)
        for row in rows
    ]


@router.get("/logs", response_model=UsageLogListResponse)
async def get_my_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    key_id: Optional[uuid.UUID] = Query(None),
):
    conditions = [UsageLog.user_id == current_user.id]
    if key_id:
        conditions.append(UsageLog.api_key_id == key_id)

    total_res = await db.execute(
        select(func.count()).select_from(UsageLog).where(*conditions)
    )
    total = total_res.scalar()

    res = await db.execute(
        select(UsageLog)
        .where(*conditions)
        .order_by(UsageLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = res.scalars().all()

    return UsageLogListResponse(
        total=total,
        items=[
            UsageLogItem(
                id=log.id,
                model=log.model,
                endpoint=log.endpoint,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                total_tokens=log.total_tokens,
                latency_ms=log.latency_ms,
                status_code=log.status_code,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
    )
