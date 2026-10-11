"""Program catalogue API."""

from __future__ import annotations

import pytest

from aceest.catalog import PROGRAMS, get_program

EXPECTED_FACTORS = {
    "fat-loss-3day": 22,
    "fat-loss-5day": 24,
    "muscle-gain-ppl": 35,
    "beginner": 26,
}


def test_catalogue_matches_baseline_factors():
    assert {code: p.calorie_factor for code, p in PROGRAMS.items()} == EXPECTED_FACTORS


def test_get_program_lookup():
    assert get_program("beginner").name == "Beginner (BG)"
    assert get_program("unknown") is None


def test_list_programs_is_public(client):
    response = client.get("/api/programs")
    assert response.status_code == 200
    programs = response.get_json()["programs"]
    assert [p["code"] for p in programs] == list(EXPECTED_FACTORS)
    assert set(programs[0]) == {"code", "name", "calorie_factor", "description"}


@pytest.mark.parametrize("code", list(EXPECTED_FACTORS))
def test_program_detail_includes_plans(client, code):
    body = client.get(f"/api/programs/{code}").get_json()
    assert body["code"] == code
    assert isinstance(body["workout"], list)
    assert body["diet"], "every program has a nutrition plan"
    assert body["color"].startswith("#")


def test_muscle_gain_plan_is_six_days(client):
    body = client.get("/api/programs/muscle-gain-ppl").get_json()
    assert len(body["workout"]) == 6
    assert body["workout"][0] == "Mon: Squat 5x5"


def test_unknown_program_returns_404(client):
    response = client.get("/api/programs/keto")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Program 'keto' not found"
