"""Calculator API endpoints."""

from __future__ import annotations


def test_calorie_calculator(client):
    response = client.post("/api/calculators/calories", json={"weight": 80, "program": "beginner"})
    assert response.status_code == 200
    assert response.get_json() == {
        "program": "beginner",
        "weight": 80.0,
        "calorie_factor": 26,
        "calories": 2080,
    }


def test_calorie_calculator_validates_input(client):
    response = client.post("/api/calculators/calories", json={"weight": -5, "program": "keto"})
    assert response.status_code == 400
    details = response.get_json()["details"]
    assert set(details) == {"weight", "program"}


def test_bmi_calculator(client):
    response = client.post("/api/calculators/bmi", json={"height": 175, "weight": 70})
    assert response.status_code == 200
    assert response.get_json()["category"] == "Normal"


def test_bmi_calculator_accepts_numeric_strings(client):
    response = client.post("/api/calculators/bmi", json={"height": "160", "weight": "100"})
    assert response.get_json()["category"] == "Obese"


def test_bmi_calculator_requires_fields(client):
    response = client.post("/api/calculators/bmi", json={})
    assert response.status_code == 400
    assert response.get_json()["details"] == {"height": "is required", "weight": "is required"}
