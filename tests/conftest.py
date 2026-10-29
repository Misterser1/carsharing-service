import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.vehicle_repository import InMemoryVehicleRepository
from app.services.vehicle_service import VehicleService


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: тесты не зависят от локального .env
    return Settings(_env_file=None, app_env="test")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def service() -> VehicleService:
    return VehicleService(InMemoryVehicleRepository())


@pytest.fixture
def vehicle_payload() -> dict:
    return {
        "model_id": 1,
        "location_id": 10,
        "plate_number": "A123BC777",
        "vin": "XW8ZZZ61ZJG000001",
        "year": 2022,
        "color": "белый",
        "feature_ids": [1, 2],
    }
