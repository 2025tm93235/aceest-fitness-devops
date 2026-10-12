"""Workout program generator: pure logic and API."""

from __future__ import annotations

import random

import pytest

from aceest.services import EXERCISE_POOL, generate_program, program_focus


@pytest.mark.parametrize(
    ("program", "focus"),
    [
        ("fat-loss-3day", "Conditioning"),
        ("fat-loss-5day", "Conditioning"),
        ("muscle-gain-ppl", "Hypertrophy"),
        ("beginner", "Full Body"),
        (None, "Full Body"),
    ],
)
def test_program_focus(program, focus):
    assert program_focus(program) == focus


@pytest.mark.parametrize(
    ("experience", "days", "per_day", "sets", "reps"),
    [
        ("beginner", 3, 3, (2, 3), (8, 12)),
        ("intermediate", 4, 4, (3, 4), (8, 15)),
        ("advanced", 5, 4, (4, 5), (6, 15)),
    ],
)
def test_generate_program_follows_experience_rules(experience, days, per_day, sets, reps):
    result = generate_program("muscle-gain-ppl", experience, random.Random(1))
    assert result.days_per_week == days
    assert len(result.plan) == days * per_day
    assert len({row["day"] for row in result.plan}) == days
    for row in result.plan:
        assert row["exercise"] in EXERCISE_POOL["Hypertrophy"]
        assert sets[0] <= row["sets"] <= sets[1]
        assert reps[0] <= row["reps"] <= reps[1]


def test_no_duplicate_exercises_within_a_day():
    result = generate_program("fat-loss-5day", "advanced", random.Random(3))
    for day in {row["day"] for row in result.plan}:
        exercises = [row["exercise"] for row in result.plan if row["day"] == day]
        assert len(exercises) == len(set(exercises))


def test_same_seed_gives_same_program():
    first = generate_program("beginner", "Beginner", random.Random(42))
    second = generate_program("beginner", "beginner", random.Random(42))
    assert first == second
    assert first.experience == "beginner"


def test_generate_program_without_rng_uses_fresh_random():
    assert generate_program(None, "beginner").days_per_week == 3


def test_generate_program_rejects_unknown_level():
    with pytest.raises(ValueError, match="experience"):
        generate_program("beginner", "expert")


@pytest.fixture
def priya(auth_client):
    auth_client.post("/api/clients", json={"name": "Priya", "program": "fat-loss-3day"})
    return auth_client


def test_generate_endpoint_requires_login(client):
    response = client.post("/api/clients/Priya/program", json={"experience": "beginner"})
    assert response.status_code == 401


def test_generate_endpoint_is_reproducible_with_seed(priya):
    payload = {"experience": "intermediate", "seed": 7}
    first = priya.post("/api/clients/Priya/program", json=payload).get_json()
    second = priya.post("/api/clients/Priya/program", json=payload).get_json()
    assert first == second
    assert first["client"] == "Priya"
    assert first["program"] == "fat-loss-3day"
    assert first["focus"] == "Conditioning"
    assert first["days_per_week"] == 4
    assert len(first["plan"]) == 16


def test_generate_endpoint_validates_input(priya):
    response = priya.post("/api/clients/Priya/program", json={"experience": "pro", "seed": -1})
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"experience", "seed"}


def test_generate_endpoint_unknown_client(auth_client):
    response = auth_client.post("/api/clients/Ghost/program", json={"experience": "beginner"})
    assert response.status_code == 404
