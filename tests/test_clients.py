"""Client CRUD API."""

from __future__ import annotations

import pytest

ARUN = {"name": "Arun", "age": 29, "height": 175, "weight": 80, "program": "muscle-gain-ppl"}


@pytest.fixture
def arun(auth_client):
    response = auth_client.post("/api/clients", json=ARUN)
    assert response.status_code == 201
    return response.get_json()


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/clients"),
        ("post", "/api/clients"),
        ("get", "/api/clients/Arun"),
        ("put", "/api/clients/Arun"),
        ("delete", "/api/clients/Arun"),
    ],
)
def test_client_endpoints_require_login(client, method, url):
    assert getattr(client, method)(url, json={}).status_code == 401


def test_create_client_computes_calories(auth_client):
    response = auth_client.post("/api/clients", json=ARUN)
    assert response.status_code == 201
    assert response.headers["Location"].endswith("/api/clients/Arun")
    body = response.get_json()
    assert body["calories"] == 2800  # 80 kg x 35
    assert body["membership_status"] == "Active"


def test_create_client_with_name_only(auth_client):
    body = auth_client.post("/api/clients", json={"name": "Meena"}).get_json()
    assert body["program"] is None
    assert body["calories"] is None


def test_create_client_validation_errors(auth_client):
    response = auth_client.post(
        "/api/clients", json={"age": 300, "weight": "heavy", "program": "keto"}
    )
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"name", "age", "weight", "program"}


def test_duplicate_client_is_rejected(auth_client, arun):
    response = auth_client.post("/api/clients", json={"name": "Arun"})
    assert response.status_code == 409


def test_list_clients_sorted_by_name(auth_client, arun):
    auth_client.post("/api/clients", json={"name": "bala"})
    names = [c["name"] for c in auth_client.get("/api/clients").get_json()["clients"]]
    assert names == ["Arun", "bala"]


def test_get_client(auth_client, arun):
    body = auth_client.get("/api/clients/Arun").get_json()
    assert body["age"] == 29


def test_get_missing_client_returns_404(auth_client):
    response = auth_client.get("/api/clients/Ghost")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Client 'Ghost' not found"


def test_partial_update_recalculates_calories(auth_client, arun):
    response = auth_client.patch("/api/clients/Arun", json={"weight": 90})
    assert response.status_code == 200
    body = response.get_json()
    assert body["weight"] == 90
    assert body["calories"] == 3150
    assert body["age"] == 29  # untouched


def test_update_can_clear_optional_field(auth_client, arun):
    body = auth_client.put("/api/clients/Arun", json={"program": None}).get_json()
    assert body["program"] is None
    assert body["calories"] is None


def test_update_can_rename_client(auth_client, arun):
    body = auth_client.put("/api/clients/Arun", json={"name": "Arun K"}).get_json()
    assert body["name"] == "Arun K"
    assert auth_client.get("/api/clients/Arun").status_code == 404


def test_update_cannot_blank_name(auth_client, arun):
    response = auth_client.put("/api/clients/Arun", json={"name": ""})
    assert response.status_code == 400
    assert response.get_json()["details"] == {"name": "is required"}


def test_rename_to_existing_client_conflicts(auth_client, arun):
    auth_client.post("/api/clients", json={"name": "Bala"})
    response = auth_client.put("/api/clients/Arun", json={"name": "Bala"})
    assert response.status_code == 409


def test_delete_client(auth_client, arun):
    assert auth_client.delete("/api/clients/Arun").status_code == 204
    assert auth_client.get("/api/clients/Arun").status_code == 404
    assert auth_client.delete("/api/clients/Arun").status_code == 404
