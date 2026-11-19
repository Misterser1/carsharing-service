"""Подключение к PostgreSQL через пул соединений (psycopg 3 + psycopg_pool).

Соединения открываются заранее и переиспользуются; размер пула ограничен DB_MAX_CONNS.
При старте приложение делает несколько попыток подключения с растущей паузой:
СУБД может быть ещё не готова, например сразу после перезапуска контейнера db.
"""

import logging
import time

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool, PoolTimeout

from app.core.config import Settings

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 3


class DatabaseUnavailableError(RuntimeError):
    """Не удалось подключиться к PostgreSQL за отведённое число попыток."""


class Database:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    @classmethod
    def connect(
        cls,
        settings: Settings,
        *,
        attempts: int | None = None,
        backoff_seconds: float = 1.0,
    ) -> "Database":
        attempts = attempts or settings.db_connect_attempts
        # make_conninfo экранирует спецсимволы пароля; сама строка нигде не логируется
        conninfo = make_conninfo(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password.get_secret_value(),
            dbname=settings.db_name,
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
            application_name=settings.app_name,
        )
        address = f"{settings.db_host}:{settings.db_port}"

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                # Пробное соединение даёт понятную ошибку (refused, auth failed и т. п.)
                with psycopg.connect(conninfo) as conn:
                    conn.execute("SELECT 1")
                pool = ConnectionPool(
                    conninfo,
                    min_size=min(2, settings.db_max_conns),  # «тёплые» соединения
                    max_size=settings.db_max_conns,  # верхняя граница пула
                    max_lifetime=30 * 60,
                    max_idle=5 * 60,
                    check=ConnectionPool.check_connection,  # отбрасывать оборванные соединения
                    name="carsharing-db",
                    open=False,
                )
                pool.open(wait=True, timeout=10)
                logger.info(
                    "[DATABASE] Successfully connected to PostgreSQL at %s (pool max %d)",
                    address,
                    settings.db_max_conns,
                )
                return cls(pool)
            except (psycopg.Error, PoolTimeout) as exc:
                last_error = exc
                if attempt == attempts:
                    break
                wait = backoff_seconds * attempt  # линейно растущая пауза
                logger.warning(
                    "[DATABASE] attempt %d/%d to %s failed: %s; retry in %.0fs",
                    attempt,
                    attempts,
                    address,
                    _short(exc),
                    wait,
                )
                time.sleep(wait)

        raise DatabaseUnavailableError(
            f"PostgreSQL at {address} is unavailable after {attempts} attempts: "
            f"{_short(last_error)}"
        )

    def ping(self, timeout: float = 2.0) -> bool:
        """Проверка доступности СУБД для /health: True, если запрос прошёл за timeout секунд."""
        try:
            with self.pool.connection(timeout=timeout) as conn:
                conn.execute("SELECT 1")
            return True
        except (psycopg.Error, PoolTimeout):
            return False

    def close(self) -> None:
        self.pool.close()


def _short(exc: Exception | None) -> str:
    # Текст ошибки psycopg бывает многострочным — в лог пишем первую строку
    return str(exc).strip().splitlines()[0] if exc else "unknown error"
