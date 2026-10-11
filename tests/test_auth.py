"""Login, logout, session guard and admin bootstrap."""

from __future__ import annotations

import logging

from aceest import create_app
from aceest.auth import create_user, verify_credentials
from aceest.db import get_db
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def test_admin_user_is_created_with_hashed_password(app):
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT password_hash, role FROM users WHERE username = ?", (ADMIN_USERNAME,))
            .fetchone()
        )
    assert row["role"] == "Admin"
    assert row["password_hash"] != ADMIN_PASSWORD
    assert row["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_admin_bootstrap_is_idempotent(tmp_path):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "a.db"), "ADMIN_PASSWORD": "x"}
    create_app(config)
    app = create_app(config)
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 1


def test_default_admin_password_logs_warning(tmp_path, caplog, monkeypatch):
    monkeypatch.delenv("ACEEST_ADMIN_PASSWORD", raising=False)
    with caplog.at_level(logging.WARNING):
        app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "d.db")})
    assert app.config["ADMIN_PASSWORD_IS_DEFAULT"] is True
    assert "default password" in caplog.text


def test_admin_password_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ACEEST_ADMIN_PASSWORD", "from-env-pass")
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "e.db")})
    assert app.config["ADMIN_PASSWORD_IS_DEFAULT"] is False
    with app.app_context():
        assert verify_credentials("admin", "from-env-pass") == "Admin"


def test_verify_credentials(app):
    with app.app_context():
        create_user("coach", "coach-pass")
        assert verify_credentials("coach", "coach-pass") == "Trainer"
        assert verify_credentials("coach", "wrong") is None
        assert verify_credentials("nobody", "coach-pass") is None


def test_login_success_returns_role(client):
    response = client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    assert response.get_json() == {"username": ADMIN_USERNAME, "role": "Admin"}


def test_login_with_wrong_password_is_rejected(client):
    response = client.post("/api/auth/login", json={"username": ADMIN_USERNAME, "password": "x"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid username or password"


def test_login_requires_both_fields(client):
    response = client.post("/api/auth/login", json={"username": ""})
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"username", "password"}


def test_login_rejects_non_json_body(client):
    response = client.post("/api/auth/login", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body must be a JSON object"


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_me_returns_current_user(auth_client):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.get_json()["username"] == ADMIN_USERNAME


def test_logout_clears_session(auth_client):
    assert auth_client.post("/api/auth/logout").status_code == 200
    assert auth_client.get("/api/auth/me").status_code == 401
