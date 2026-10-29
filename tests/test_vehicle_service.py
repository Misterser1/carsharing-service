"""Бизнес-правила проверяются без HTTP и без настоящей БД."""

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.vehicle import VehicleStatus


def test_create_normalizes_plate_and_vin(service, vehicle_payload):
    vehicle = service.create_vehicle(**{**vehicle_payload, "plate_number": " a123bc777 "})

    assert vehicle.plate_number == "A123BC777"
    assert vehicle.status == VehicleStatus.AVAILABLE
    assert vehicle.fuel_level_pct == 100


def test_duplicate_plate_is_conflict(service, vehicle_payload):
    service.create_vehicle(**vehicle_payload)

    with pytest.raises(ConflictError) as exc:
        service.create_vehicle(**{**vehicle_payload, "vin": "XW8ZZZ61ZJG000002"})
    assert exc.value.code == "VEHICLE_ALREADY_EXISTS"


def test_duplicate_vin_is_conflict(service, vehicle_payload):
    service.create_vehicle(**vehicle_payload)

    with pytest.raises(ConflictError):
        service.create_vehicle(**{**vehicle_payload, "plate_number": "B456CD777"})


def test_get_missing_vehicle(service):
    from uuid import uuid4

    with pytest.raises(NotFoundError):
        service.get_vehicle(uuid4())


def test_operator_can_send_to_maintenance_and_back(service, vehicle_payload):
    vehicle = service.create_vehicle(**vehicle_payload)

    vehicle = service.update_vehicle(vehicle.id, {"status": VehicleStatus.MAINTENANCE})
    assert vehicle.status == VehicleStatus.MAINTENANCE
    vehicle = service.update_vehicle(vehicle.id, {"status": VehicleStatus.AVAILABLE})
    assert vehicle.status == VehicleStatus.AVAILABLE


@pytest.mark.parametrize(
    "target", [VehicleStatus.RESERVED, VehicleStatus.RENTED, VehicleStatus.DECOMMISSIONED]
)
def test_status_set_only_by_scenarios(service, vehicle_payload, target):
    vehicle = service.create_vehicle(**vehicle_payload)

    with pytest.raises(ConflictError) as exc:
        service.update_vehicle(vehicle.id, {"status": target})
    assert exc.value.code == "INVALID_STATUS_TRANSITION"


def test_odometer_cannot_decrease(service, vehicle_payload):
    vehicle = service.create_vehicle(**vehicle_payload)
    service.update_vehicle(vehicle.id, {"odometer_km": 1500})

    with pytest.raises(ConflictError) as exc:
        service.update_vehicle(vehicle.id, {"odometer_km": 1000})
    assert exc.value.code == "ODOMETER_DECREASE"


def test_decommission_is_idempotent(service, vehicle_payload):
    vehicle = service.create_vehicle(**vehicle_payload)

    service.decommission_vehicle(vehicle.id)
    service.decommission_vehicle(vehicle.id)

    stored = service.get_vehicle(vehicle.id)
    assert stored.status == VehicleStatus.DECOMMISSIONED
    assert stored.location_id is None


def test_cannot_decommission_rented_vehicle(service, vehicle_payload):
    vehicle = service.create_vehicle(**vehicle_payload)
    # RENTED ставит сценарий аренды (будущие ЛР); здесь — напрямую через репозиторий
    vehicle.status = VehicleStatus.RENTED
    service._repository.update(vehicle)

    with pytest.raises(ConflictError) as exc:
        service.decommission_vehicle(vehicle.id)
    assert exc.value.code == "VEHICLE_IN_USE"


def test_cannot_edit_decommissioned_vehicle(service, vehicle_payload):
    vehicle = service.create_vehicle(**vehicle_payload)
    service.decommission_vehicle(vehicle.id)

    with pytest.raises(ConflictError) as exc:
        service.update_vehicle(vehicle.id, {"color": "чёрный"})
    assert exc.value.code == "VEHICLE_DECOMMISSIONED"
