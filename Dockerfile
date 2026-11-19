# syntax=docker/dockerfile:1

# --- Этап сборки (Builder): зависимости ставятся в отдельное виртуальное окружение ---
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Сначала только список зависимостей: этот слой берётся из кэша,
# пока requirements.txt не меняется, даже если поменялся код
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Финальный лёгкий этап: только Python, готовые зависимости и код ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8080

# Приложение работает не от root
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Копируем установленные зависимости из этапа сборки, без pip-кэша и инструментов
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER appuser

# Открываем порт приложения
EXPOSE 8080

# Docker сам проверяет здоровье контейнера через health-эндпоинт
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('HTTP_PORT', '8080') + '/api/v1/health', timeout=2)" || exit 1

# Команда запуска: хост и порт берутся из HTTP_HOST / HTTP_PORT
CMD ["python", "-m", "app"]
