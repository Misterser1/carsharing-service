"""Точка сборки приложения: настройки → логирование → хранилища → роутеры."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import health
from app.api.errors import register_error_handlers
from app.api.middleware import register_request_id
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.repositories.vehicle_repository import InMemoryVehicleRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Carsharing / Rental API",
        description="REST API сервиса краткосрочной аренды автомобилей.",
        version=settings.app_version,
        debug=settings.app_debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.state.settings = settings
    app.state.started_at = time.monotonic()
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


app = create_app()
