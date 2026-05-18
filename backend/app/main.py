from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import get_redis, close_redis
from app.core.logger import setup_logging

logger = setup_logging()
from app.api.v1.router import api_router
from app.api.v1.proxy import router as proxy_router


async def run_dev_migrations():
    """Apply incremental schema changes for dev (ALTER TABLE IF NOT EXISTS).
    In production, use Alembic instead.
    """
    from app.core.database import engine
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS provider_id UUID REFERENCES providers(id) ON DELETE SET NULL;"
        ))
        await conn.execute(text(
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS provider_id UUID REFERENCES providers(id) ON DELETE SET NULL;"
        ))
        await conn.execute(text(
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS plaintext_key VARCHAR(100);"
        ))
        await conn.execute(text(
            "ALTER TABLE models DROP CONSTRAINT IF EXISTS models_name_key;"
        ))
        await conn.execute(text(
            "ALTER TABLE key_applications ADD COLUMN IF NOT EXISTS requested_models JSONB DEFAULT '[]'::jsonb;"
        ))
        await conn.execute(text(
            "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS allowed_models JSONB DEFAULT '[]'::jsonb;"
        ))
    print("[startup] Dev migrations applied.")


async def seed_superadmin():
    """Ensure the default superadmin account exists on startup."""
    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.SUPER_ADMIN_USERNAME)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            admin = User(
                email=settings.SUPER_ADMIN_EMAIL,
                display_name=settings.SUPER_ADMIN_DISPLAY_NAME,
                username=settings.SUPER_ADMIN_USERNAME,
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
                role="superadmin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            print(f"[startup] Created superadmin: {settings.SUPER_ADMIN_USERNAME}")
        else:
            print(f"[startup] Superadmin already exists: {settings.SUPER_ADMIN_USERNAME}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await run_dev_migrations()
    await seed_superadmin()
    await get_redis()  # warm up connection
    print("[startup] AI Gateway Proxy is ready!")
    yield
    # Shutdown
    await close_redis()
    print("[shutdown] AI Gateway Proxy stopped.")



app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="OpenAI API Gateway Proxy with Microsoft OAuth2 authentication",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (prefixed with /api/v1)
app.include_router(api_router, prefix="/api/v1")

# Proxy routes (no prefix — directly /v1/...)
app.include_router(proxy_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
