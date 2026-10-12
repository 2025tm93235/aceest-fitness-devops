"""Workout and exercise logging."""

from __future__ import annotations

from datetime import date

import pytest

SESSION = {
    "date": "2026-03-02",
    "workout_type": "Strength",
    "duration_min": 75,
    "notes": "Felt strong",
    "exercises": [
        {"name": "Squat", "sets": 5, "reps": 5, "weight": 100},
        {"name": "Bench Press", "sets": 5, "reps": 5, "weight": 70},
    ],
}


@pytest.fixture
def karthik(auth_client):
    auth_client.post("/api/clients", json={"name": "Karthik"})
    return auth_client


def test_workouts_require_login(client):
    assert client.post("/api/clients/Karthik/workouts", json=SESSION).status_code == 401


def test_log_workout_with_exercises(karthik):
    response = karthik.post("/api/clients/Karthik/workouts", json=SESSION)
    assert response.status_code == 201
    workout = response.get_json()
    assert workout["workout_type"] == "Strength"
    assert workout["duration_min"] == 75
    assert [e["name"] for e in workout["exercises"]] == ["Squat", "Bench Press"]
    assert workout["exercises"][0] == {"name": "Squat", "sets": 5, "reps": 5, "weight": 100.0}


def test_log_workout_defaults(karthik):
    workout = karthik.post(
        "/api/clients/Karthik/workouts", json={"workout_type": "Cardio"}
    ).get_json()
    assert workout["date"] == date.today().isoformat()
    assert workout["duration_min"] == 60
    assert workout["exercises"] == []


def test_log_workout_validates_session_fields(karthik):
    response = karthik.post(
        "/api/clients/Karthik/workouts",
        json={"workout_type": "Yoga", "date": "yesterday", "duration_min": 0},
    )
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"workout_type", "date", "duration_min"}


def test_log_workout_validates_each_exercise(karthik):
    payload = {
        "workout_type": "Strength",
        "exercises": [{"name": "Squat", "sets": 0}, "deadlift", {"reps": 5}],
    }
    response = karthik.post("/api/clients/Karthik/workouts", json=payload)
    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "exercises[0].sets": "must be at least 1",
        "exercises[1]": "must be an object",
        "exercises[2].name": "is required",
    }


def test_log_workout_exercises_must_be_list(karthik):
    response = karthik.post(
        "/api/clients/Karthik/workouts",
        json={"workout_type": "Strength", "exercises": "squats"},
    )
    assert response.get_json()["details"] == {"exercises": "must be a list"}


def test_invalid_workout_is_not_partially_saved(karthik):
    karthik.post(
        "/api/clients/Karthik/workouts",
        json={"workout_type": "Strength", "exercises": [{"name": ""}]},
    )
    assert karthik.get("/api/clients/Karthik/workouts").get_json()["workouts"] == []


def test_workout_history_newest_first(karthik):
    for day in ("2026-03-01", "2026-03-05", "2026-03-03"):
        karthik.post(
            "/api/clients/Karthik/workouts", json={"workout_type": "Mobility", "date": day}
        )
    history = karthik.get("/api/clients/Karthik/workouts").get_json()["workouts"]
    assert [w["date"] for w in history] == ["2026-03-05", "2026-03-03", "2026-03-01"]


def test_workouts_for_unknown_client(auth_client):
    assert auth_client.get("/api/clients/Ghost/workouts").status_code == 404
