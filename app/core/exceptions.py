"""Ошибки предметной области.

Сервисный слой бросает эти исключения и ничего не знает про HTTP.
Перевод в коды ответа делает API-слой (app/api/errors.py).
"""

from typing import Any


class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """Запрошенный объект не существует."""


class ConflictError(DomainError):
    """Операция противоречит текущему состоянию (дубликат, недопустимый переход статуса)."""
