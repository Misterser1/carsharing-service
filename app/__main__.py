"""Запуск: python -m app (хост и порт берутся из HTTP_HOST / HTTP_PORT)."""

import uvicorn

from app.core.config import get_settings

if __name__ == "__main__":
    # Сначала читаем конфигурацию: при пропущенной переменной запуск остановится здесь
    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.http_host,
        port=settings.http_port,
        reload=settings.http_reload,
        log_level=settings.log_level.lower(),
    )
