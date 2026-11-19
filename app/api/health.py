import time

from fastapi import APIRouter, Request, Response, status

from app.api.deps import DatabaseDep, SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка доступности сервиса и БД",
    responses={503: {"model": HealthResponse, "description": "PostgreSQL недоступна"}},
)
def get_health(
    request: Request, response: Response, settings: SettingsDep, database: DatabaseDep
) -> HealthResponse:
    db_up = database.ping()
    if not db_up:
        # Балансировщик и оркестратор по 503 понимают, что экземпляр сейчас не обслуживает запросы
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="pass" if db_up else "fail",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=int(time.monotonic() - request.app.state.started_at),
        db="up" if db_up else "down",
    )
