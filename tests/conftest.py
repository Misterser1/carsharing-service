import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.vehicle_repository import InMemoryVehicleRepository
from app.services.vehicle_service import VehicleService

DB_ENV = {
    "db_host": "localhost",
    "db_user": "test_user",
    "db_password": "test_password",
    "db_name": "test_db",
}


class FakeDatabase:
    """Подменяет PostgreSQL в тестах API: доступность задаётся флагом."""

    def __init__(self, up: bool = True) -> None:
        self.up = up
        self.closed = False

    def ping(self, timeout: float = 2.0) -> bool:
        return self.up

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: тесты не зависят от локального .env
    return Settings(_env_file=None, app_env="test", **DB_ENV)


@pytest.fixture
def database() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def client(settings: Settings, database: FakeDatabase) -> TestClient:
    return TestClient(create_app(settings, database=database))


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
