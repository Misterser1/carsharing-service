"""HTTP-слой автопарка: разбирает запрос, вызывает сервис, собирает ответ.

Бизнес-правил и работы с хранилищем здесь нет — только вызов VehicleService.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import VehicleServiceDep
from app.models.vehicle import VehicleStatus
from app.schemas.common import ErrorResponse
from app.schemas.vehicle import (
    VehicleCreateRequest,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdateRequest,
)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

ERRORS = {
    400: {"model": ErrorResponse, "description": "Ошибка валидации запроса"},
    404: {"model": ErrorResponse, "description": "Автомобиль не найден"},
    409: {"model": ErrorResponse, "description": "Конфликт состояния"},
}


@router.get(
    "",
    response_model=VehicleListResponse,
    summary="Список автомобилей",
    responses={400: ERRORS[400]},
)
def list_vehicles(
    service: VehicleServiceDep,
    status_filter: Annotated[VehicleStatus | None, Query(alias="status")] = None,
    location_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VehicleListResponse:
    items, total = service.list_vehicles(
        status=status_filter, location_id=location_id, page=page, page_size=page_size
    )
    return VehicleListResponse(
        items=[VehicleResponse.model_validate(v) for v in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить автомобиль в автопарк",
    responses={400: ERRORS[400], 409: ERRORS[409]},
)
def create_vehicle(body: VehicleCreateRequest, service: VehicleServiceDep) -> VehicleResponse:
    vehicle = service.create_vehicle(**body.model_dump())
    return VehicleResponse.model_validate(vehicle)


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Получить автомобиль",
    responses={404: ERRORS[404]},
)
def get_vehicle(vehicle_id: UUID, service: VehicleServiceDep) -> VehicleResponse:
    return VehicleResponse.model_validate(service.get_vehicle(vehicle_id))


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    summary="Изменить автомобиль или его статус",
    responses=ERRORS,
)
def update_vehicle(
    vehicle_id: UUID, body: VehicleUpdateRequest, service: VehicleServiceDep
) -> VehicleResponse:
    vehicle = service.update_vehicle(vehicle_id, body.model_dump(exclude_unset=True))
    return VehicleResponse.model_validate(vehicle)


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Списать автомобиль",
    responses={404: ERRORS[404], 409: ERRORS[409]},
)
def decommission_vehicle(vehicle_id: UUID, service: VehicleServiceDep) -> Response:
    service.decommission_vehicle(vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
