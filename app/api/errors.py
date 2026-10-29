"""Единый формат ошибок ErrorResponse и перевод доменных исключений в HTTP-коды."""

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ConflictError, DomainError, NotFoundError

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

DOMAIN_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}


def error_response(
    request: Request, status_code: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {"code": code, "message": message, "details": details or {}, "request_id": request_id}
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = DOMAIN_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return error_response(request, status_code, exc.code, exc.message, exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # По спецификации ошибки валидации — 400, а не 422 (по умолчанию в FastAPI).
    errors = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        request,
        status.HTTP_400_BAD_REQUEST,
        "VALIDATION_ERROR",
        "Ошибка валидации запроса",
        {"errors": errors},
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return error_response(
        request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Необработанная ошибка: %s %s", request.method, request.url.path)
    return error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "Внутренняя ошибка сервера",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
