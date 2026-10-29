"""Конфигурация приложения из переменных окружения (и файла .env).

Имя поля = имя переменной окружения без учёта регистра: app_name ← APP_NAME, http_port ← HTTP_PORT.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    http_port: int = 8000

    cors_origins: Annotated[list[str], NoDecode] = []

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
