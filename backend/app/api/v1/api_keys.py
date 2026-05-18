import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyCreatedResponse, APIKeyListResponse
from app.services.key_service import create_api_key, invalidate_key_cache
from app.dependencies import get_current_user

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.get("", response_model=APIKeyListResponse)
async def list_my_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    total_res = await db.execute(
        select(func.count()).select_from(APIKey).where(APIKey.user_id == current_user.id)
    )
    total = total_res.scalar()

    res = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    keys = res.scalars().all()
    return APIKeyListResponse(total=total, items=keys)


@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_api_key(db, current_user.id, body)


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return key


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_key(
    key_id: uuid.UUID,
    body: APIKeyUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    update_data = body.model_dump(exclude_unset=True)
    # Users can only rename their key; admins handle status/limits via admin routes
    allowed_fields = {"name"}
    for field in allowed_fields:
        if field in update_data:
            setattr(key, field, update_data[field])

    await db.commit()
    await db.refresh(key)
    await invalidate_key_cache(key.key_hash)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    key.status = "revoked"
    await db.commit()
    await invalidate_key_cache(key.key_hash)
