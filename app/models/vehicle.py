"""Доменная сущность «Автомобиль».

Пока это обычный dataclass: хранилище в памяти. В ЛР5–6 появится ORM-модель для PostgreSQL.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class VehicleStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    RENTED = "RENTED"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Vehicle:
    model_id: int
    plate_number: str
    vin: str
    year: int
    color: str
    location_id: int | None = None
    feature_ids: list[int] = field(default_factory=list)
    status: VehicleStatus = VehicleStatus.AVAILABLE
    odometer_km: int = 0
    fuel_level_pct: int = 100
    latitude: float | None = None
    longitude: float | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
