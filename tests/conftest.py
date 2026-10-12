"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from aceest import create_app

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "S3cure-test-pass"


@pytest.fixture
def app(tmp_path):
    """A fresh application instance with an isolated temporary database."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.db"),
            "ADMIN_USERNAME": ADMIN_USERNAME,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
            "ADMIN_PASSWORD_IS_DEFAULT": False,
            # Fast hash for tests only; production keeps the scrypt default.
            "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client with an authenticated admin session."""
    response = client.post(
        "/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return client
