"""Version visibility: /version endpoint, response headers and UI footer."""

from __future__ import annotations

import aceest
from aceest import create_app
from aceest.config import load_config


def test_version_endpoint_reports_version_track_and_instance(app):
    app.config.update(DEPLOYMENT_TRACK="canary", INSTANCE_NAME="aceest-canary-abc")
    body = app.test_client().get("/version").get_json()
    assert body == {
        "version": aceest.__version__,
        "track": "canary",
        "instance": "aceest-canary-abc",
    }


def test_every_response_carries_version_headers(client):
    for path in ("/health", "/api/programs", "/login"):
        response = client.get(path)
        assert response.headers["X-App-Version"] == aceest.__version__
        assert response.headers["X-Deployment-Track"] == "local"


def test_footer_shows_version_track_and_instance(client):
    page = client.get("/login").get_data(as_text=True)
    assert f"v{aceest.__version__}" in page
    assert "local" in page


def test_track_and_pod_name_come_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOYMENT_TRACK", "blue")
    monkeypatch.setenv("POD_NAME", "aceest-blue-7d9f")
    config = load_config()
    assert config["DEPLOYMENT_TRACK"] == "blue"
    assert config["INSTANCE_NAME"] == "aceest-blue-7d9f"
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "v.db")})
    assert app.test_client().get("/version").get_json()["track"] == "blue"


def test_instance_name_defaults_to_hostname(monkeypatch):
    monkeypatch.delenv("POD_NAME", raising=False)
    monkeypatch.delenv("DEPLOYMENT_TRACK", raising=False)
    config = load_config()
    assert config["DEPLOYMENT_TRACK"] == "local"
    assert config["INSTANCE_NAME"]
