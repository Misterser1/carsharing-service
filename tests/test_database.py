"""Подключение к PostgreSQL: повторные попытки и поведение приложения при недоступной БД.

Интеграционный тест с настоящей СУБД запускается, если задан TEST_DB_HOST
(например, при поднятом `docker compose up -d db`): TEST_DB_HOST=localhost pytest.
"""

import logging
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Database, DatabaseUnavailableError
from app.main import create_app
from tests.conftest import DB_ENV


@pytest.fixture
def unreachable(settings: Settings) -> Settings:
    # на порту 1 никто не слушает — соединение сразу отклоняется
    return settings.model_copy(update={"db_host": "127.0.0.1", "db_port": 1})


def test_connect_retries_then_fails(unreachable, caplog):
    caplog.set_level(logging.WARNING, logger="app.core.database")

    with pytest.raises(DatabaseUnavailableError, match="after 3 attempts"):
        Database.connect(unreachable, attempts=3, backoff_seconds=0)

    retries = [r.getMessage() for r in caplog.records if "attempt" in r.getMessage()]
    assert len(retries) == 2  # после третьей, последней попытки — уже ошибка, а не повтор
    assert retries[0].startswith("[DATABASE] attempt 1/3 to 127.0.0.1:1 failed")


def test_password_not_in_error_message(unreachable):
    with pytest.raises(DatabaseUnavailableError) as exc:
        Database.connect(unreachable, attempts=1)

    assert "test_password" not in str(exc.value)


def test_app_does_not_start_without_database(unreachable):
    app = create_app(unreachable.model_copy(update={"db_connect_attempts": 1}))
    with pytest.raises(DatabaseUnavailableError):
        # вход в контекст запускает lifespan, то есть подключение к БД при старте
        with TestClient(app):
            pass


@pytest.mark.skipif(not os.getenv("TEST_DB_HOST"), reason="нужна настоящая PostgreSQL")
def test_real_database():
    settings = Settings(
        _env_file=None,
        **{
            **DB_ENV,
            "db_host": os.environ["TEST_DB_HOST"],
            "db_port": int(os.getenv("TEST_DB_PORT", "5432")),
            "db_user": os.getenv("TEST_DB_USER", DB_ENV["db_user"]),
            "db_password": os.getenv("TEST_DB_PASSWORD", DB_ENV["db_password"]),
            "db_name": os.getenv("TEST_DB_NAME", DB_ENV["db_name"]),
            "db_max_conns": 3,
        },
    )
    database = Database.connect(settings, attempts=1)
    try:
        assert database.ping()
        assert database.pool.max_size == 3
    finally:
        database.close()
