"""Authentication: hashed credentials, admin bootstrap and the login guard.

Replaces the legacy v3.x login, which stored ``admin/admin`` in plain text.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from flask import Flask, current_app, session
from werkzeug.security import check_password_hash, generate_password_hash

from aceest.db import get_db
from aceest.errors import ApiError

F = TypeVar("F", bound=Callable[..., Any])

# Used to spend comparable time when the username does not exist, so response
# timing does not reveal which usernames are valid.
_DUMMY_HASH = generate_password_hash("aceest-timing-equaliser")


def _hash_method() -> str:
    return current_app.config.get("PASSWORD_HASH_METHOD", "scrypt")


def create_user(username: str, password: str, role: str = "Trainer") -> None:
    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password, method=_hash_method()), role),
    )
    db.commit()


def verify_credentials(username: str, password: str) -> str | None:
    """Return the user's role if the credentials are valid, else ``None``."""
    row = (
        get_db()
        .execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        .fetchone()
    )
    if row is None:
        check_password_hash(_DUMMY_HASH, password)
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return row["role"]


def ensure_admin_user(app: Flask) -> None:
    """Create the bootstrap admin account on first start-up."""
    username = app.config["ADMIN_USERNAME"]
    with app.app_context():
        exists = get_db().execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            return
        create_user(username, app.config["ADMIN_PASSWORD"], role="Admin")
    if app.config.get("ADMIN_PASSWORD_IS_DEFAULT"):
        app.logger.warning(
            "Admin user '%s' created with the default password; "
            "set ACEEST_ADMIN_PASSWORD in shared environments.",
            username,
        )


def current_user() -> dict[str, str] | None:
    return session.get("user")


def login_user(username: str, role: str) -> None:
    session.clear()
    session["user"] = {"username": username, "role": role}


def logout_user() -> None:
    session.clear()


def login_required(view: F) -> F:
    """Reject unauthenticated requests with HTTP 401."""

    @functools.wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user() is None:
            raise ApiError("Authentication required", status=401)
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]


def init_app(app: Flask) -> None:
    ensure_admin_user(app)
