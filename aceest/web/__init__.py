"""Server-rendered HTML pages (Jinja2) for trainers and admins."""

from __future__ import annotations

import hmac
import secrets

from flask import Blueprint, Flask, abort, request, session

bp = Blueprint("web", __name__)

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def csrf_token() -> str:
    """Per-session token embedded in every HTML form."""
    token = session.get(CSRF_SESSION_KEY)
    if token is None:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


@bp.before_request
def verify_csrf_token() -> None:
    if request.method != "POST":
        return
    expected = session.get(CSRF_SESSION_KEY, "")
    submitted = request.form.get(CSRF_FORM_FIELD, "")
    if not expected or not hmac.compare_digest(expected, submitted):
        abort(400, description="Invalid or missing CSRF token. Reload the page and try again.")


def init_app(app: Flask) -> None:
    # Importing the view modules attaches their routes to ``bp``.
    from aceest.web import views  # noqa: F401

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.register_blueprint(bp)
