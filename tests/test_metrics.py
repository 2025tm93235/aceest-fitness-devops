"""Body metrics, client BMI and the metrics part of the summary."""

from __future__ import annotations

from datetime import date

import pytest


@pytest.fixture
def divya(auth_client):
    auth_client.post("/api/clients", json={"name": "Divya", "height": 165, "weight": 68})
    return auth_client


def test_metrics_require_login(client):
    assert client.get("/api/clients/Divya/metrics").status_code == 401


def test_log_metric(divya):
    response = divya.post(
        "/api/clients/Divya/metrics",
        json={"date": "2026-04-01", "weight": 67.5, "waist": 80, "bodyfat": 27.5},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["weight"] == 67.5
    assert body["bodyfat"] == 27.5


def test_log_partial_metric_defaults_to_today(divya):
    body = divya.post("/api/clients/Divya/metrics", json={"waist": 79}).get_json()
    assert body["date"] == date.today().isoformat()
    assert body["weight"] is None


def test_metric_requires_at_least_one_measurement(divya):
    response = divya.post("/api/clients/Divya/metrics", json={"date": "2026-04-01"})
    assert response.status_code == 400
    assert "metrics" in response.get_json()["details"]


def test_metric_ranges_are_validated(divya):
    response = divya.post("/api/clients/Divya/metrics", json={"bodyfat": 90, "waist": 5})
    assert set(response.get_json()["details"]) == {"bodyfat", "waist"}


def test_metrics_listed_chronologically(divya):
    for day, weight in (("2026-04-15", 66), ("2026-04-01", 68), ("2026-04-08", 67)):
        divya.post("/api/clients/Divya/metrics", json={"date": day, "weight": weight})
    metrics = divya.get("/api/clients/Divya/metrics").get_json()["metrics"]
    assert [m["weight"] for m in metrics] == [68, 67, 66]


def test_summary_includes_latest_metric(divya):
    assert divya.get("/api/clients/Divya/summary").get_json()["latest_metrics"] is None
    divya.post("/api/clients/Divya/metrics", json={"date": "2026-04-15", "weight": 66})
    divya.post("/api/clients/Divya/metrics", json={"date": "2026-04-01", "weight": 68})
    latest = divya.get("/api/clients/Divya/summary").get_json()["latest_metrics"]
    assert latest["date"] == "2026-04-15"


def test_client_bmi(divya):
    body = divya.get("/api/clients/Divya/bmi").get_json()
    assert body == {
        "client": "Divya",
        "bmi": 25.0,
        "category": "Overweight",
        "risk": "Moderate risk; focus on adherence and progressive activity.",
    }


def test_client_bmi_needs_height_and_weight(auth_client):
    auth_client.post("/api/clients", json={"name": "Sam", "weight": 70})
    response = auth_client.get("/api/clients/Sam/bmi")
    assert response.status_code == 422


def test_metrics_for_unknown_client(auth_client):
    assert auth_client.post("/api/clients/Ghost/metrics", json={"weight": 70}).status_code == 404
