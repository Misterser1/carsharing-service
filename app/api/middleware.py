import uuid

from fastapi import FastAPI, Request

from app.api.errors import REQUEST_ID_HEADER


def register_request_id(app: FastAPI) -> None:
    """Присваивает каждому запросу request_id: он попадает в ErrorResponse и заголовок ответа."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = _incoming_or_new(request.headers.get(REQUEST_ID_HEADER))
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response


def _incoming_or_new(value: str | None) -> str:
    # Берём id от клиента или балансировщика, только если это UUID (так в спецификации).
    try:
        return str(uuid.UUID(value)) if value else str(uuid.uuid4())
    except ValueError:
        return str(uuid.uuid4())
