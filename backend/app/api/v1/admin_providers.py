"""
Admin-only routes for Provider and KeyApplication management.
Appended to the existing admin router in admin.py.
"""
import uuid
import httpx
from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.provider import Provider
from app.models.key_application import KeyApplication
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.provider import (
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderListResponse, SyncedModel
)
from app.schemas.key_application import (
    KeyApplicationReview, KeyApplicationResponse, KeyApplicationListResponse
)
from app.dependencies import require_admin
from app.services.key_service import create_api_key, invalidate_key_cache
from app.schemas.api_key import APIKeyCreate
from app.services.proxy_service import fetch_provider_models
from app.core.redis_client import get_redis

router = APIRouter(prefix="/admin", tags=["Admin Providers & Applications"])


# ── Providers ──────────────────────────────────────────────────────────────────

@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    total = (await db.execute(select(func.count()).select_from(Provider))).scalar()
    res = await db.execute(
        select(Provider).order_by(Provider.sort_order.asc(), Provider.name.asc()).offset(skip).limit(limit)
    )
    providers = res.scalars().all()
    return ProviderListResponse(total=total, items=providers)


@router.post("/providers", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: ProviderCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await db.execute(select(Provider).where(Provider.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Provider '{body.name}' already exists")
    provider = Provider(**body.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.patch("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = res.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(provider, k, v)
    await db.commit()
    await db.refresh(provider)
    # Invalidate Redis cache for this provider
    redis = await get_redis()
    await redis.delete(f"provider:{provider_id}")
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = res.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
    redis = await get_redis()
    await redis.delete(f"provider:{provider_id}")


@router.get("/providers/{provider_id}/sync-models", response_model=list[SyncedModel])
async def sync_provider_models(
    provider_id: uuid.UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Fetch available models from the upstream provider API."""
    res = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = res.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    try:
        models = await fetch_provider_models(provider.base_url, provider.api_key)
        return [SyncedModel(**m) for m in models]
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream returned {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to reach provider: {str(e)}")


# ── Applications ────────────────────────────────────────────────────────────────

def _build_app_response(app: KeyApplication) -> KeyApplicationResponse:
    return KeyApplicationResponse(
        id=app.id,
        user_id=app.user_id,
        provider_id=app.provider_id,
        requested_models=app.requested_models,
        reason=app.reason,
        intended_use=app.intended_use,
        status=app.status,
        admin_note=app.admin_note,
        reviewed_by=app.reviewed_by,
        reviewed_at=app.reviewed_at,
        api_key_id=app.api_key_id,
        created_at=app.created_at,
        updated_at=app.updated_at,
        provider_name=app.provider.name if app.provider else None,
        provider_display_name=app.provider.display_name if app.provider else None,
        user_email=app.user.email if app.user else None,
        user_display_name=app.user.display_name if app.user else None,
    )


@router.get("/applications", response_model=KeyApplicationListResponse)
async def list_applications(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    conditions = []
    if status_filter:
        conditions.append(KeyApplication.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(KeyApplication).where(*conditions))).scalar()
    res = await db.execute(
        select(KeyApplication)
        .options(joinedload(KeyApplication.provider))
        .where(*conditions)
        .order_by(KeyApplication.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    apps = res.scalars().all()
    return KeyApplicationListResponse(total=total, items=[_build_app_response(a) for a in apps])


@router.post("/applications/{app_id}/review", response_model=KeyApplicationResponse)
async def review_application(
    app_id: uuid.UUID,
    body: KeyApplicationReview,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be 'approved' or 'rejected'")

    res = await db.execute(select(KeyApplication).where(KeyApplication.id == app_id))
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != "pending":
        raise HTTPException(status_code=400, detail=f"Application is already '{app.status}'")

    app.status = body.status
    app.admin_note = body.admin_note
    app.reviewed_by = admin.id
    app.reviewed_at = datetime.utcnow()

    # Auto-create API key on approval
    if body.status == "approved":
        new_key = await create_api_key(
            db=db,
            user_id=app.user_id,
            data=APIKeyCreate(
                name=f"Approved: {app.reason[:60]}",
                rate_limit_rpm=60,
                token_limit_daily=0,
                allowed_models=app.requested_models,
            ),
            provider_id=app.provider_id,
        )
        app.api_key_id = new_key.id

    await db.commit()
    await db.refresh(app)
    return _build_app_response(app)
