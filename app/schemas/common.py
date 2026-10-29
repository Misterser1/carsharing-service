from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(examples=["VEHICLE_NOT_FOUND"])
    message: str = Field(examples=["Автомобиль не найден"])
    details: dict[str, Any] = {}
    request_id: UUID


class HealthResponse(BaseModel):
    # pass / fail — как в формате Health Check Response (draft-inadarei-api-health-check)
    status: Literal["pass"] = "pass"
    app_name: str = Field(examples=["Carsharing Rental API"])
    version: str = Field(examples=["1.0.0"])
    environment: str = Field(examples=["development"])
    uptime_seconds: int = Field(ge=0)
