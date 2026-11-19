"""Точка сборки приложения: настройки → логирование → БД и хранилища → роутеры.

Запуск через фабрику: `uvicorn app.main:create_app --factory` (так делает `python -m app`).
Модульной переменной `app` нет, чтобы импорт не требовал заданных переменных окружения.
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import health
from app.api.errors import register_error_handlers
from app.api.middleware import register_request_id
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database, DatabaseUnavailableError
from app.core.logging import setup_logging
from app.repositories.vehicle_repository import InMemoryVehicleRepository

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    """database передают тесты; по умолчанию подключение создаётся при старте приложения."""
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    logger.info("[CONFIG] Environment variables loaded successfully")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.database is None:
            try:
                app.state.database = await run_in_threadpool(Database.connect, settings)
            except DatabaseUnavailableError as exc:
                logger.error("[DATABASE] %s", exc)
                raise
        logger.info("[HTTP] Server starting on port %s", settings.http_port)
        yield
        app.state.database.close()

    app = FastAPI(
        title="Carsharing / Rental API",
        description="REST API сервиса краткосрочной аренды автомобилей.",
        version=settings.app_version,
        debug=settings.app_debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.started_at = time.monotonic()
    app.state.database = database
    # Автопарк пока хранится в памяти; репозиторий на PostgreSQL — в ЛР6
    app.state.vehicle_repository = InMemoryVehicleRepository()

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_request_id(app)
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        # Корень ведёт на документацию, а в production (где /docs выключен) — на health-check
        return RedirectResponse("/docs" if settings.docs_enabled else "/api/v1/health")

    return app
