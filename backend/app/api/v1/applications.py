"""User-facing routes: list providers, list models by provider, submit/view applications."""
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.provider import Provider
from app.models.model import Model
from app.models.key_application import KeyApplication
from app.schemas.provider import ProviderPublic, ProviderPublicListResponse
from app.schemas.model import ModelResponse, ModelListResponse
from app.schemas.key_application import (
    KeyApplicationCreate, KeyApplicationResponse, KeyApplicationListResponse
)

router = APIRouter(tags=["Applications & Providers"])


# ── Public provider listing ─────────────────────────────────────────────────────

@router.get("/providers", response_model=ProviderPublicListResponse)
async def list_enabled_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return all enabled providers (no api_key exposed)."""
    total = (
        await db.execute(select(func.count()).select_from(Provider).where(Provider.is_enabled == True))
    ).scalar()
    res = await db.execute(
        select(Provider)
        .where(Provider.is_enabled == True)
        .order_by(Provider.sort_order.asc(), Provider.name.asc())
    )
    providers = res.scalars().all()
    return ProviderPublicListResponse(total=total, items=providers)


@router.get("/models", response_model=ModelListResponse)
async def list_all_enabled_models(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=2000),
):
    """Return all enabled models (for dropdown population in the UI)."""
    total = (
        await db.execute(select(func.count()).select_from(Model).where(Model.is_enabled == True))
    ).scalar()
    res = await db.execute(
        select(Model)
        .where(Model.is_enabled == True)
        .order_by(Model.sort_order.asc(), Model.name.asc())
        .offset(skip).limit(limit)
    )
    models = res.scalars().all()
    return ModelListResponse(total=total, items=models)



@router.get("/providers/{provider_id}/models", response_model=ModelListResponse)
async def list_models_for_provider(
    provider_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return enabled models for a specific provider."""
    provider_exists = await db.execute(
        select(Provider).where(Provider.id == provider_id, Provider.is_enabled == True)
    )
    if not provider_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    total = (
        await db.execute(
            select(func.count()).select_from(Model)
            .where(Model.provider_id == provider_id, Model.is_enabled == True)
        )
    ).scalar()
    res = await db.execute(
        select(Model)
        .where(Model.provider_id == provider_id, Model.is_enabled == True)
        .order_by(Model.sort_order.asc(), Model.name.asc())
    )
    models = res.scalars().all()
    return ModelListResponse(total=total, items=models)


# ── Applications ────────────────────────────────────────────────────────────────

def _app_to_response(app: KeyApplication) -> KeyApplicationResponse:
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
    )


@router.post("/applications", response_model=KeyApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    body: KeyApplicationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit a new API access application."""
    # Check provider exists and is enabled
    prov = await db.execute(
        select(Provider).where(Provider.id == body.provider_id, Provider.is_enabled == True)
    )
    provider_obj = prov.scalar_one_or_none()
    if not provider_obj:
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    # Check for existing pending application to same provider
    existing = await db.execute(
        select(KeyApplication).where(
            KeyApplication.user_id == current_user.id,
            KeyApplication.provider_id == body.provider_id,
            KeyApplication.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="You already have a pending application for this provider"
        )

    app = KeyApplication(
        user_id=current_user.id,
        provider_id=body.provider_id,
        requested_models=body.requested_models,
        reason=body.reason,
        intended_use=body.intended_use,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    app.provider = provider_obj
    return _app_to_response(app)


@router.get("/applications", response_model=KeyApplicationListResponse)
async def my_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List the current user's own applications."""
    total = (
        await db.execute(
            select(func.count()).select_from(KeyApplication)
            .where(KeyApplication.user_id == current_user.id)
        )
    ).scalar()
    res = await db.execute(
        select(KeyApplication)
        .options(joinedload(KeyApplication.provider))
        .where(KeyApplication.user_id == current_user.id)
        .order_by(KeyApplication.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    apps = res.scalars().all()
    return KeyApplicationListResponse(total=total, items=[_app_to_response(a) for a in apps])


@router.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_application(
    app_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Withdraw a pending application."""
    res = await db.execute(
        select(KeyApplication).where(
            KeyApplication.id == app_id,
            KeyApplication.user_id == current_user.id,
        )
    )
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending applications can be withdrawn")
    await db.delete(app)
    await db.commit()
