from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Any
import secrets


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Gateway Proxy"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_gateway"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Microsoft OAuth2 ──────────────────────────────────────────────────────
    AZURE_CLIENT_ID: str = "your-azure-client-id"
    AZURE_CLIENT_SECRET: str = "your-azure-client-secret"
    AZURE_TENANT_ID: str = "your-azure-tenant-id"
    AZURE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/callback"


    # ── Super Admin (Local Auth) ───────────────────────────────────────────────
    SUPER_ADMIN_USERNAME: str = "openai"
    SUPER_ADMIN_PASSWORD: str = "openai"
    SUPER_ADMIN_EMAIL: str = "admin@ai-gateway.local"
    SUPER_ADMIN_DISPLAY_NAME: str = "Super Admin"

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Can be a JSON array or comma-separated string in .env
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            # Support comma-separated string from env var
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
