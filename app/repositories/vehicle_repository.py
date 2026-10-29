"""Слой доступа к данным для автомобилей.

Сервис зависит от абстракции VehicleRepository, а не от конкретного хранилища.
Сейчас подключена реализация в памяти; в ЛР6 её заменит репозиторий на PostgreSQL
без изменений в сервисе и API.
"""

import copy
import threading
from abc import ABC, abstractmethod
from uuid import UUID

from app.models.vehicle import Vehicle, VehicleStatus


class VehicleRepository(ABC):
    @abstractmethod
    def add(self, vehicle: Vehicle) -> Vehicle: ...

    @abstractmethod
    def get(self, vehicle_id: UUID) -> Vehicle | None: ...

    @abstractmethod
    def get_by_plate_number(self, plate_number: str) -> Vehicle | None: ...

    @abstractmethod
    def get_by_vin(self, vin: str) -> Vehicle | None: ...

    @abstractmethod
    def list(
        self,
        *,
        status: VehicleStatus | None,
        location_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Vehicle], int]:
        """Возвращает страницу автомобилей и общее число найденных."""

    @abstractmethod
    def update(self, vehicle: Vehicle) -> Vehicle: ...


class InMemoryVehicleRepository(VehicleRepository):
    """Хранит автомобили в словаре. Данные пропадают при перезапуске."""

    def __init__(self) -> None:
        self._items: dict[UUID, Vehicle] = {}
        self._lock = threading.Lock()

    # Наружу отдаём копии, чтобы изменения сохранялись только через update().
    def add(self, vehicle: Vehicle) -> Vehicle:
        with self._lock:
            self._items[vehicle.id] = copy.deepcopy(vehicle)
        return copy.deepcopy(vehicle)

    def get(self, vehicle_id: UUID) -> Vehicle | None:
        with self._lock:
            vehicle = self._items.get(vehicle_id)
            return copy.deepcopy(vehicle) if vehicle else None

    def get_by_plate_number(self, plate_number: str) -> Vehicle | None:
        return self._find(lambda v: v.plate_number == plate_number)

    def get_by_vin(self, vin: str) -> Vehicle | None:
        return self._find(lambda v: v.vin == vin)

    def list(
        self,
        *,
        status: VehicleStatus | None,
        location_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Vehicle], int]:
        with self._lock:
            found = [
                v
                for v in self._items.values()
                if (status is None or v.status == status)
                and (location_id is None or v.location_id == location_id)
            ]
        found.sort(key=lambda v: v.created_at)
        page = found[offset : offset + limit]
        return [copy.deepcopy(v) for v in page], len(found)

    def update(self, vehicle: Vehicle) -> Vehicle:
        with self._lock:
            self._items[vehicle.id] = copy.deepcopy(vehicle)
        return copy.deepcopy(vehicle)

    def _find(self, predicate) -> Vehicle | None:
        with self._lock:
            for vehicle in self._items.values():
                if predicate(vehicle):
                    return copy.deepcopy(vehicle)
        return None
