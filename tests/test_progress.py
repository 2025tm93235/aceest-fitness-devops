"""Weekly adherence tracking and client summary."""

from __future__ import annotations

from datetime import date

import pytest

from aceest.services import week_label


@pytest.fixture
def meena(auth_client):
    auth_client.post(
        "/api/clients",
        json={
            "name": "Meena",
            "weight": 60,
            "program": "beginner",
            "target_weight": 55,
            "target_adherence": 85,
        },
    )
    return auth_client


def test_week_label_format():
    assert week_label(date(2026, 2, 16)) == "Week 07 - 2026"


def test_progress_requires_login(client):
    assert client.get("/api/clients/Meena/progress").status_code == 401


def test_log_progress_defaults_to_current_week(meena):
    response = meena.post("/api/clients/Meena/progress", json={"adherence": 80})
    assert response.status_code == 201
    entry = response.get_json()
    assert entry["adherence"] == 80
    assert entry["week"] == week_label(date.today())


def test_log_progress_with_explicit_week(meena):
    entry = meena.post(
        "/api/clients/Meena/progress", json={"adherence": 70, "week": "Week 01 - 2026"}
    ).get_json()
    assert entry["week"] == "Week 01 - 2026"


@pytest.mark.parametrize("adherence", [-1, 101, "high", None])
def test_log_progress_validates_adherence(meena, adherence):
    response = meena.post("/api/clients/Meena/progress", json={"adherence": adherence})
    assert response.status_code == 400


def test_log_progress_for_unknown_client(auth_client):
    response = auth_client.post("/api/clients/Ghost/progress", json={"adherence": 50})
    assert response.status_code == 404


def test_list_progress_in_logged_order(meena):
    for value in (60, 75, 90):
        meena.post("/api/clients/Meena/progress", json={"adherence": value})
    entries = meena.get("/api/clients/Meena/progress").get_json()["progress"]
    assert [e["adherence"] for e in entries] == [60, 75, 90]


def test_summary_without_progress(meena):
    summary = meena.get("/api/clients/Meena/summary").get_json()
    assert summary["client"]["name"] == "Meena"
    assert summary["program"]["code"] == "beginner"
    assert summary["goals"] == {"target_weight": 55.0, "target_adherence": 85}
    assert summary["progress"] == {"weeks_logged": 0, "average_adherence": 0}


def test_summary_averages_adherence(meena):
    for value in (70, 80, 85):
        meena.post("/api/clients/Meena/progress", json={"adherence": value})
    summary = meena.get("/api/clients/Meena/summary").get_json()
    assert summary["progress"] == {"weeks_logged": 3, "average_adherence": 78.3}


def test_summary_for_client_without_program(auth_client):
    auth_client.post("/api/clients", json={"name": "Ravi"})
    summary = auth_client.get("/api/clients/Ravi/summary").get_json()
    assert summary["program"] is None


def test_deleting_client_removes_progress(meena, app):
    meena.post("/api/clients/Meena/progress", json={"adherence": 50})
    meena.delete("/api/clients/Meena")
    from aceest.db import get_db

    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM progress").fetchone()[0] == 0
