from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class OAuthCallbackParams(BaseModel):
    code: str
    state: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None
