"""Бизнес-логика автопарка.

Здесь живут правила предметной области: уникальность госномера и VIN,
допустимые переходы статусов, запрет списания автомобиля в аренде.
Сервис не знает ни про HTTP, ни про то, где хранятся данные.
"""

from typing import Any
from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.models.vehicle import Vehicle, VehicleStatus, utcnow
from app.repositories.vehicle_repository import VehicleRepository

# Статусы, которые оператор может выставить вручную через PATCH.
# RESERVED и RENTED ставит только сценарий аренды, DECOMMISSIONED — только списание (DELETE).
MANUAL_TRANSITIONS: dict[VehicleStatus, set[VehicleStatus]] = {
    VehicleStatus.AVAILABLE: {VehicleStatus.MAINTENANCE},
    VehicleStatus.MAINTENANCE: {VehicleStatus.AVAILABLE},
}

IN_USE = {VehicleStatus.RESERVED, VehicleStatus.RENTED}


class VehicleService:
    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    def list_vehicles(
        self,
        *,
        status: VehicleStatus | None = None,
        location_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Vehicle], int]:
        return self._repository.list(
            status=status,
            location_id=location_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def get_vehicle(self, vehicle_id: UUID) -> Vehicle:
        vehicle = self._repository.get(vehicle_id)
        if vehicle is None:
            raise NotFoundError(
                "VEHICLE_NOT_FOUND",
                "Автомобиль не найден",
                {"vehicle_id": str(vehicle_id)},
            )
        return vehicle

    def create_vehicle(
        self,
        *,
        model_id: int,
        plate_number: str,
        vin: str,
        year: int,
        color: str,
        location_id: int | None = None,
        feature_ids: list[int] | None = None,
    ) -> Vehicle:
        plate_number = plate_number.strip().upper()
        vin = vin.strip().upper()

        if self._repository.get_by_plate_number(plate_number):
            raise ConflictError(
                "VEHICLE_ALREADY_EXISTS",
                "Автомобиль с таким госномером уже зарегистрирован",
                {"plate_number": plate_number},
            )
        if self._repository.get_by_vin(vin):
            raise ConflictError(
                "VEHICLE_ALREADY_EXISTS",
                "Автомобиль с таким VIN уже зарегистрирован",
                {"vin": vin},
            )

        vehicle = Vehicle(
            model_id=model_id,
            plate_number=plate_number,
            vin=vin,
            year=year,
            color=color,
            location_id=location_id,
            feature_ids=list(dict.fromkeys(feature_ids or [])),
        )
        return self._repository.add(vehicle)

    def update_vehicle(self, vehicle_id: UUID, changes: dict[str, Any]) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)

        if vehicle.status == VehicleStatus.DECOMMISSIONED:
            raise ConflictError("VEHICLE_DECOMMISSIONED", "Списанный автомобиль нельзя изменить")

        new_status = changes.get("status")
        if new_status is not None and new_status != vehicle.status:
            allowed = MANUAL_TRANSITIONS.get(vehicle.status, set())
            if new_status not in allowed:
                raise ConflictError(
                    "INVALID_STATUS_TRANSITION",
                    f"Нельзя перевести автомобиль из {vehicle.status} в {new_status}",
                    {"from": vehicle.status, "to": new_status},
                )

        new_odometer = changes.get("odometer_km")
        if new_odometer is not None and new_odometer < vehicle.odometer_km:
            raise ConflictError(
                "ODOMETER_DECREASE",
                "Пробег не может уменьшиться",
                {"current": vehicle.odometer_km, "requested": new_odometer},
            )

        for field_name, value in changes.items():
            setattr(vehicle, field_name, value)
        vehicle.updated_at = utcnow()
        return self._repository.update(vehicle)

    def decommission_vehicle(self, vehicle_id: UUID) -> None:
        vehicle = self.get_vehicle(vehicle_id)

        if vehicle.status == VehicleStatus.DECOMMISSIONED:
            return  # повторное списание ничего не меняет: DELETE идемпотентен
        if vehicle.status in IN_USE:
            raise ConflictError(
                "VEHICLE_IN_USE",
                "Нельзя списать автомобиль, который забронирован или в аренде",
                {"status": vehicle.status},
            )

        vehicle.status = VehicleStatus.DECOMMISSIONED
        vehicle.location_id = None
        vehicle.updated_at = utcnow()
        self._repository.update(vehicle)
