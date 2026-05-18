import uuid
from typing import Annotated, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.api_key import APIKey
from app.models.usage_log import UsageLog
from app.models.model import Model
from app.schemas.user import UserResponse, UserUpdate, UserListResponse
from app.schemas.api_key import APIKeyResponse, APIKeyUpdate, APIKeyListResponse
from app.schemas.stats import (
    AdminStatsSummary, DailyUsage, ModelUsage, KeyUsageSummary,
    UserTokenRankingResponse, UserTokenRankingItem
)
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse, ModelListResponse
from app.dependencies import require_admin
from app.services.key_service import invalidate_key_cache

router = APIRouter(prefix="/admin", tags=["Admin"])



# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    conditions = []
    if search:
        conditions.append(
            User.email.ilike(f"%{search}%") | User.display_name.ilike(f"%{search}%")
        )

    total_res = await db.execute(
        select(func.count()).select_from(User).where(*conditions)
    )
    total = total_res.scalar()

    res = await db.execute(
        select(User).where(*conditions).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = res.scalars().all()
    return UserListResponse(total=total, items=users)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent non-superadmins from modifying superadmins
    if user.role == "superadmin" and admin.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify superadmin")

    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data:
        user.password_hash = get_password_hash(update_data.pop("password"))
    for k, v in update_data.items():
        setattr(user, k, v)

    await db.commit()
    await db.refresh(user)
    return user


# ── API Keys ───────────────────────────────────────────────────────────────────

@router.get("/keys", response_model=APIKeyListResponse)
async def list_all_keys(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    conditions = []
    if user_id:
        conditions.append(APIKey.user_id == user_id)
    if status_filter:
        conditions.append(APIKey.status == status_filter)

    total_res = await db.execute(
        select(func.count()).select_from(APIKey).where(*conditions)
    )
    total = total_res.scalar()

    res = await db.execute(
        select(APIKey).where(*conditions).order_by(APIKey.created_at.desc()).offset(skip).limit(limit)
    )
    keys = res.scalars().all()
    return APIKeyListResponse(total=total, items=keys)


@router.patch("/keys/{key_id}", response_model=APIKeyResponse)
async def admin_update_key(
    key_id: uuid.UUID,
    body: APIKeyUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(key, k, v)

    await db.commit()
    await db.refresh(key)
    await invalidate_key_cache(key.key_hash)
    return key


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_key(
    key_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await db.delete(key)
    await db.commit()
    await invalidate_key_cache(key.key_hash)


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/summary", response_model=AdminStatsSummary)
async def admin_summary(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    users_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    total_keys = (await db.execute(select(func.count()).select_from(APIKey))).scalar()
    active_keys = (
        await db.execute(select(func.count()).select_from(APIKey).where(APIKey.status == "active"))
    ).scalar()

    total_tokens_res = await db.execute(
        select(func.coalesce(func.sum(UsageLog.total_tokens), 0), func.count(UsageLog.id))
    )
    total_tokens, total_requests = total_tokens_res.one()

    today_res = await db.execute(
        select(
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.count(UsageLog.id),
        ).where(UsageLog.created_at >= today_start)
    )
    today_tokens, today_requests = today_res.one()

    return AdminStatsSummary(
        total_users=users_count,
        total_keys=total_keys,
        active_keys=active_keys,
        total_tokens_all_time=total_tokens,
        total_requests_all_time=total_requests,
        today_tokens=today_tokens,
        today_requests=today_requests,
    )


@router.get("/analytics/daily", response_model=list[DailyUsage])
async def admin_daily_usage(
    admin: Annotated[User, Depends(require_admin)],
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
        .where(UsageLog.created_at >= start_date)
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


@router.get("/analytics/models", response_model=list[ModelUsage])
async def admin_model_usage(
    admin: Annotated[User, Depends(require_admin)],
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
        .where(UsageLog.created_at >= start_date)
        .group_by(UsageLog.model)
        .order_by(func.sum(UsageLog.total_tokens).desc())
    )
    return [
        ModelUsage(model=r.model, total_tokens=r.total_tokens, request_count=r.request_count)
        for r in res.all()
    ]


@router.get("/analytics/users/ranking", response_model=UserTokenRankingResponse)
async def admin_user_ranking(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
):
    res = await db.execute(
        select(
            User.id.label("user_id"),
            User.email,
            User.display_name,
            func.coalesce(func.sum(UsageLog.total_tokens), 0).label("total_tokens"),
            func.count(UsageLog.id).label("request_count"),
        )
        .join(UsageLog, UsageLog.user_id == User.id)
        .group_by(User.id, User.email, User.display_name)
        .order_by(func.sum(UsageLog.total_tokens).desc())
        .limit(limit)
    )
    
    items = [
        UserTokenRankingItem(
            user_id=r.user_id,
            email=r.email,
            display_name=r.display_name,
            total_tokens=r.total_tokens,
            request_count=r.request_count,
        )
        for r in res.all()
    ]
    return UserTokenRankingResponse(items=items)


@router.get("/analytics/top-keys", response_model=list[KeyUsageSummary])
async def admin_top_keys(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
):
    start_date = datetime.utcnow() - timedelta(days=days)
    res = await db.execute(
        select(
            UsageLog.api_key_id,
            APIKey.key_prefix,
            APIKey.name,
            func.coalesce(func.sum(UsageLog.total_tokens), 0).label("total_tokens"),
            func.count(UsageLog.id).label("request_count"),
        )
        .join(APIKey, UsageLog.api_key_id == APIKey.id)
        .where(UsageLog.created_at >= start_date)
        .group_by(UsageLog.api_key_id, APIKey.key_prefix, APIKey.name)
        .order_by(func.sum(UsageLog.total_tokens).desc())
        .limit(limit)
    )
    return [
        KeyUsageSummary(
            key_id=str(r.api_key_id),
            key_prefix=r.key_prefix,
            key_name=r.name,
            total_tokens=r.total_tokens,
            request_count=r.request_count,
        )
        for r in res.all()
    ]


# ── Model Management ───────────────────────────────────────────────────────────

@router.get("/models", response_model=ModelListResponse)
async def list_all_models(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    total_res = await db.execute(select(func.count()).select_from(Model))
    total = total_res.scalar()

    res = await db.execute(
        select(Model).order_by(Model.sort_order.asc(), Model.name.asc()).offset(skip).limit(limit)
    )
    models = res.scalars().all()
    return ModelListResponse(total=total, items=models)


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    body: ModelCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await db.execute(select(Model).where(Model.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{body.name}' already exists",
        )
    model = Model(**body.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.patch("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: uuid.UUID,
    body: ModelUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Model).where(Model.id == model_id))
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(model, k, v)

    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Model).where(Model.id == model_id))
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    await db.delete(model)
    await db.commit()
