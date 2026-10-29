from fastapi import APIRouter

from app.api import health
from app.api.v1 import vehicles

api_router = APIRouter(prefix="/api/v1")
# /api/v1/health — по заданию ЛР3; /health без префикса тоже остаётся (для балансировщика)
api_router.include_router(health.router)
api_router.include_router(vehicles.router)
