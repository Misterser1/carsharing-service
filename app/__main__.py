"""Запуск: python -m app (хост и порт берутся из HTTP_HOST / HTTP_PORT)."""

import uvicorn

from app.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
