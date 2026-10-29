import time

from fastapi import APIRouter, Request

from app.api.deps import SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Проверка доступности сервиса")
def get_health(request: Request, settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=int(time.monotonic() - request.app.state.started_at),
    )
