"""Конфигурация приложения из переменных окружения (и файла .env).

Имя поля = имя переменной окружения без учёта регистра: app_name ← APP_NAME, db_host ← DB_HOST.
Поля без значения по умолчанию обязательны: если такая переменная не задана,
приложение не запускается и пишет, какой переменной не хватает.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Ошибки pydantic, которые для переменной окружения означают «не задана»
NOT_SET_ERRORS = {"missing", "string_too_short"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Carsharing Rental API"
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "1.0.0"
    app_debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    http_host: str = "0.0.0.0"
    http_port: int = 8080
    http_reload: bool = False  # автоперезагрузка при правке кода — только для локальной разработки

    cors_origins: Annotated[list[str], NoDecode] = []

    # PostgreSQL. Пароль — SecretStr: не попадает в логи и repr(settings)
    db_host: str = Field(min_length=1)
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_user: str = Field(min_length=1)
    db_password: SecretStr = Field(min_length=1)
    db_name: str = Field(min_length=1)
    db_max_conns: int = Field(default=10, ge=1)
    db_connect_attempts: int = Field(default=10, ge=1)  # попыток подключения при старте

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        # В .env удобнее писать список через запятую, а не JSON.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


class ConfigError(Exception):
    """Конфигурация неполная или некорректная — запускать приложение нельзя."""


def load_settings(**overrides) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise ConfigError(_describe(exc)) from None


def _describe(exc: ValidationError) -> str:
    not_set: list[str] = []
    invalid: list[str] = []
    for error in exc.errors():
        name = str(error["loc"][0]).upper()
        if error["type"] in NOT_SET_ERRORS:
            not_set.append(name)
        else:
            invalid.append(f"{name}: {error['msg']}")

    parts = []
    if not_set:
        parts.append("не заданы обязательные переменные окружения: " + ", ".join(not_set))
    if invalid:
        parts.append("некорректные значения: " + "; ".join(invalid))
    return "; ".join(parts)


@lru_cache
def get_settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        # Без конфигурации работать нельзя: останавливаем запуск с понятным сообщением
        raise SystemExit(f"[CONFIG] {exc}") from None
