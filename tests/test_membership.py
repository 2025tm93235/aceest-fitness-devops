"""Membership status: pure logic and API."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from aceest.services import membership_state

TODAY = date(2026, 6, 15)


@pytest.mark.parametrize(
    ("status", "end", "effective", "days"),
    [
        ("Active", "2026-07-15", "Active", 30),
        ("Active", "2026-06-15", "Active", 0),  # last day still active
        ("Active", "2026-06-14", "Expired", -1),
        ("Active", None, "Active", None),  # open-ended membership
        ("Inactive", "2026-12-31", "Inactive", 199),
    ],
)
def test_membership_state(status, end, effective, days):
    state = membership_state(status, end, TODAY)
    assert state["effective_status"] == effective
    assert state["days_remaining"] == days
    assert state["is_active"] is (effective == "Active")


@pytest.fixture
def lakshmi(auth_client):
    auth_client.post("/api/clients", json={"name": "Lakshmi"})
    return auth_client


def test_new_client_membership_defaults_to_active(lakshmi):
    body = lakshmi.get("/api/clients/Lakshmi/membership").get_json()
    assert body == {
        "client": "Lakshmi",
        "status": "Active",
        "effective_status": "Active",
        "membership_end": None,
        "days_remaining": None,
        "is_active": True,
    }


def test_expired_membership_is_reported(lakshmi):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    lakshmi.patch("/api/clients/Lakshmi", json={"membership_end": yesterday})
    body = lakshmi.get("/api/clients/Lakshmi/membership").get_json()
    assert body["effective_status"] == "Expired"
    assert body["is_active"] is False


def test_membership_fields_validated_on_create(auth_client):
    response = auth_client.post(
        "/api/clients",
        json={"name": "X", "membership_status": "Gold", "membership_end": "soon"},
    )
    assert set(response.get_json()["details"]) == {"membership_status", "membership_end"}


def test_membership_status_cannot_be_cleared(lakshmi):
    response = lakshmi.patch("/api/clients/Lakshmi", json={"membership_status": ""})
    assert response.status_code == 400
    assert response.get_json()["details"] == {"membership_status": "is required"}


def test_membership_can_be_deactivated(lakshmi):
    lakshmi.patch("/api/clients/Lakshmi", json={"membership_status": "Inactive"})
    body = lakshmi.get("/api/clients/Lakshmi/membership").get_json()
    assert body["effective_status"] == "Inactive"


def test_membership_requires_login(client):
    assert client.get("/api/clients/Lakshmi/membership").status_code == 401


def test_membership_unknown_client(auth_client):
    assert auth_client.get("/api/clients/Ghost/membership").status_code == 404
