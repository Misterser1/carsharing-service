"""Сборка зависимостей для обработчиков (Dependency Injection через FastAPI Depends)."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.repositories.vehicle_repository import VehicleRepository
from app.services.vehicle_service import VehicleService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_vehicle_repository(request: Request) -> VehicleRepository:
    return request.app.state.vehicle_repository


def get_vehicle_service(
    repository: Annotated[VehicleRepository, Depends(get_vehicle_repository)],
) -> VehicleService:
    return VehicleService(repository)


SettingsDep = Annotated[Settings, Depends(get_settings)]
VehicleServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]
