"""Gym-wide statistics: repository, API and dashboard cards (release 1.2.0)."""

from __future__ import annotations

from datetime import date, timedelta


def _seed(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post("/api/clients", json={"name": "Arun", "program": "beginner", "weight": 70})
    client.post("/api/clients", json={"name": "Bala", "program": "beginner"})
    client.post(
        "/api/clients",
        json={"name": "Chitra", "program": "muscle-gain-ppl", "membership_end": yesterday},
    )
    client.post("/api/clients/Arun/progress", json={"adherence": 80})
    client.post("/api/clients/Bala/progress", json={"adherence": 65})
    client.post("/api/clients/Arun/workouts", json={"workout_type": "Strength"})


def test_stats_require_login(client):
    assert client.get("/api/stats").status_code == 401


def test_stats_on_empty_gym(auth_client):
    assert auth_client.get("/api/stats").get_json() == {
        "total_clients": 0,
        "active_memberships": 0,
        "average_adherence": 0,
        "workouts_logged": 0,
        "clients_by_program": {},
    }


def test_stats_summarise_clients_progress_and_workouts(auth_client):
    _seed(auth_client)
    stats = auth_client.get("/api/stats").get_json()
    assert stats["total_clients"] == 3
    assert stats["active_memberships"] == 2  # Chitra's membership has expired
    assert stats["average_adherence"] == 72.5
    assert stats["workouts_logged"] == 1
    assert stats["clients_by_program"] == {"Beginner (BG)": 2, "Muscle Gain (MG) - PPL": 1}


def test_client_without_program_is_not_counted_by_program(auth_client):
    auth_client.post("/api/clients", json={"name": "Devi"})
    stats = auth_client.get("/api/stats").get_json()
    assert stats["total_clients"] == 1
    assert stats["clients_by_program"] == {}


def test_dashboard_shows_stat_cards(client):
    from tests.test_web import web_login

    web_login(client)
    _seed(client)
    page = client.get("/").get_data(as_text=True)
    assert "Active memberships" in page
    assert "72.5%" in page
    assert "Workouts logged" in page
