"""JSON REST API blueprint (mounted under ``/api``)."""

from __future__ import annotations

from flask import Blueprint, Flask

bp = Blueprint("api", __name__, url_prefix="/api")


def init_app(app: Flask) -> None:
    # Importing the route modules attaches their views to ``bp``.
    from aceest.api import (  # noqa: F401
        auth,
        calculators,
        clients,
        health,
        metrics,
        programs,
        progress,
        workouts,
    )

    app.register_blueprint(bp)
    app.register_blueprint(health.bp)
