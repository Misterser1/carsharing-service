from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
def test_health(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["status"] == "pass"
    assert body["app_name"] == "Carsharing Rental API"
    assert body["version"] == "1.0.0"
    assert body["environment"] == "test"
    assert body["uptime_seconds"] >= 0
    assert body["db"] == "up"
    UUID(response.headers["X-Request-ID"])


@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
def test_health_is_503_when_db_is_down(client, database, path):
    database.up = False

    response = client.get(path)

    assert response.status_code == 503
    assert response.json()["status"] == "fail"
    assert response.json()["db"] == "down"


def test_vehicle_crud(client, vehicle_payload):
    created = client.post("/api/v1/vehicles", json=vehicle_payload)
    assert created.status_code == 201
    vehicle = created.json()
    assert vehicle["status"] == "AVAILABLE"

    got = client.get(f"/api/v1/vehicles/{vehicle['id']}")
    assert got.status_code == 200
    assert got.json()["plate_number"] == "A123BC777"

    patched = client.patch(f"/api/v1/vehicles/{vehicle['id']}", json={"status": "MAINTENANCE"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "MAINTENANCE"

    deleted = client.delete(f"/api/v1/vehicles/{vehicle['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/api/v1/vehicles/{vehicle['id']}").json()["status"] == "DECOMMISSIONED"


def test_list_with_filter_and_pagination(client, vehicle_payload):
    for i in range(3):
        client.post(
            "/api/v1/vehicles",
            json={**vehicle_payload, "plate_number": f"A{i}00BC777", "vin": f"XW8ZZZ61ZJG00000{i}"},
        )
    first_id = client.get("/api/v1/vehicles").json()["items"][0]["id"]
    client.patch(f"/api/v1/vehicles/{first_id}", json={"status": "MAINTENANCE"})

    page = client.get("/api/v1/vehicles", params={"page": 1, "page_size": 2}).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2

    available = client.get("/api/v1/vehicles", params={"status": "AVAILABLE"}).json()
    assert available["total"] == 2


def test_not_found_uses_error_response(client):
    response = client.get(f"/api/v1/vehicles/{uuid4()}")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "VEHICLE_NOT_FOUND"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_validation_error_is_400(client, vehicle_payload):
    response = client.post("/api/v1/vehicles", json={**vehicle_payload, "vin": "short"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["errors"][0]["field"] == "body.vin"


def test_empty_patch_is_400(client, vehicle_payload):
    vehicle_id = client.post("/api/v1/vehicles", json=vehicle_payload).json()["id"]

    assert client.patch(f"/api/v1/vehicles/{vehicle_id}", json={}).status_code == 400
    assert client.patch(f"/api/v1/vehicles/{vehicle_id}", json={"color": None}).status_code == 400


def test_duplicate_is_409(client, vehicle_payload):
    client.post("/api/v1/vehicles", json=vehicle_payload)
    response = client.post("/api/v1/vehicles", json=vehicle_payload)

    assert response.status_code == 409
    assert response.json()["code"] == "VEHICLE_ALREADY_EXISTS"


def test_unknown_route_uses_error_response(client):
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_docs_disabled_in_prod(settings, database):
    prod_settings = settings.model_copy(update={"app_env": "production"})
    prod = TestClient(create_app(prod_settings, database=database))

    assert prod.get("/docs").status_code == 404
    assert prod.get("/", follow_redirects=False).headers["location"] == "/api/v1/health"


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
