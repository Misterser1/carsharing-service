"""Схемы запросов и ответов /api/v1/vehicles (соответствуют openapi.yaml)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.vehicle import VehicleStatus


class VehicleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: int
    location_id: int | None = None
    plate_number: str = Field(min_length=1, max_length=12, examples=["A123BC777"])
    vin: str = Field(min_length=17, max_length=17, examples=["XW8ZZZ61ZJG000001"])
    year: int = Field(ge=2000)
    color: str = Field(min_length=1, max_length=30)
    feature_ids: list[int] = []


class VehicleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: int | None = None
    color: str | None = Field(default=None, min_length=1, max_length=30)
    status: VehicleStatus | None = None
    odometer_km: int | None = Field(default=None, ge=0)
    fuel_level_pct: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "VehicleUpdateRequest":
        # minProperties: 1 из спецификации
        if not self.model_fields_set:
            raise ValueError("Нужно передать хотя бы одно поле")
        # null допустим только для location_id (авто сняли с парковки)
        for name in self.model_fields_set - {"location_id"}:
            if getattr(self, name) is None:
                raise ValueError(f"Поле {name} не может быть null")
        return self


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: int
    location_id: int | None
    plate_number: str
    vin: str
    year: int
    color: str
    feature_ids: list[int]
    status: VehicleStatus
    odometer_km: int
    fuel_level_pct: int
    latitude: float | None
    longitude: float | None
    created_at: datetime
    updated_at: datetime


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    page: int
    page_size: int
    total: int
