import secrets
from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.oauth import get_auth_url, get_token_from_code, get_user_info
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def local_login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Username/password login for local accounts (super admin)."""
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/oauth/redirect")
async def oauth_redirect():
    """Return Microsoft OAuth2 redirect URL."""
    state = secrets.token_urlsafe(16)
    auth_url = get_auth_url(state)
    return {"url": auth_url, "state": state}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle Microsoft OAuth2 callback, create/update user, issue JWT."""
    result = get_token_from_code(code)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error_description", "OAuth error"),
        )

    access_token = result.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token returned")

    ms_user = get_user_info(access_token)
    microsoft_id = ms_user.get("id")
    email = ms_user.get("mail") or ms_user.get("userPrincipalName", "")
    display_name = ms_user.get("displayName", email)

    # Upsert user
    res = await db.execute(select(User).where(User.microsoft_id == microsoft_id))
    user = res.scalar_one_or_none()

    if not user:
        # Check by email in case they were pre-created
        res2 = await db.execute(select(User).where(User.email == email))
        user = res2.scalar_one_or_none()

    if user:
        user.microsoft_id = microsoft_id
        user.display_name = display_name
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    else:
        user = User(
            microsoft_id=microsoft_id,
            email=email,
            display_name=display_name,
            role="user",
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Redirect to frontend with token
    frontend_url = f"{settings.FRONTEND_URL}/oauth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_url)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
