"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from aceest import create_app


@pytest.fixture
def app(tmp_path):
    """A fresh application instance with an isolated temporary database."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.db"),
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()
