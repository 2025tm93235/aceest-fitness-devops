"""Authentication endpoints (session cookie based)."""

from __future__ import annotations

from flask import jsonify

from aceest.api import bp
from aceest.auth import current_user, login_required, login_user, logout_user, verify_credentials
from aceest.errors import ApiError
from aceest.validation import Validator, json_body


@bp.post("/auth/login")
def login():
    data = (
        Validator(json_body())
        .string("username", required=True, max_length=50)
        .string("password", required=True, max_length=128)
        .validate()
    )
    role = verify_credentials(data["username"], data["password"])
    if role is None:
        raise ApiError("Invalid username or password", status=401)
    login_user(data["username"], role)
    return jsonify(username=data["username"], role=role)


@bp.post("/auth/logout")
def logout():
    logout_user()
    return jsonify(message="Logged out")


@bp.get("/auth/me")
@login_required
def me():
    return jsonify(current_user())
