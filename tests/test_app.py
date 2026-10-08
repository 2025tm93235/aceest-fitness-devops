"""Application factory, configuration and error handling."""

from __future__ import annotations

import importlib

import aceest
from aceest import create_app
from aceest.config import load_config


def test_health_endpoint_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["service"] == "aceest-fitness"
    assert body["version"] == aceest.__version__
    assert body["database"] == "ok"


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_unknown_page_returns_html_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.mimetype == "text/html"


def test_method_not_allowed_on_health_is_json(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert response.is_json


def test_config_reads_secret_from_environment(monkeypatch):
    monkeypatch.setenv("ACEEST_SECRET_KEY", "from-env")
    monkeypatch.setenv("ACEEST_SECURE_COOKIES", "true")
    config = load_config()
    assert config["SECRET_KEY"] == "from-env"
    assert config["SESSION_COOKIE_SECURE"] is True


def test_config_generates_random_secret_when_unset(monkeypatch):
    monkeypatch.delenv("ACEEST_SECRET_KEY", raising=False)
    monkeypatch.delenv("ACEEST_SECURE_COOKIES", raising=False)
    first, second = load_config(), load_config()
    assert first["SECRET_KEY"] != second["SECRET_KEY"]
    assert len(first["SECRET_KEY"]) == 64
    assert first["SESSION_COOKIE_SECURE"] is False


def test_test_config_overrides_defaults():
    app = create_app({"TESTING": True, "SECRET_KEY": "override"})
    assert app.config["SECRET_KEY"] == "override"
    assert app.testing is True


def test_wsgi_entry_point_exposes_app(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("app")
    module = importlib.reload(module)
    assert module.app.name == "aceest"


def test_api_error_is_rendered_as_json(app):
    from aceest.errors import ApiError

    @app.get("/api/_boom")
    def boom():
        raise ApiError("Bad thing", status=422, details={"field": "reason"})

    response = app.test_client().get("/api/_boom")
    assert response.status_code == 422
    assert response.get_json() == {"error": "Bad thing", "details": {"field": "reason"}}


def test_api_error_without_details_omits_key():
    from aceest.errors import ApiError

    assert ApiError("plain").to_dict() == {"error": "plain"}
