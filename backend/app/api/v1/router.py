from fastapi import APIRouter
from app.api.v1 import auth, api_keys, proxy, stats, admin, applications
from app.api.v1 import admin_providers

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(api_keys.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
api_router.include_router(admin_providers.router)
api_router.include_router(applications.router)
