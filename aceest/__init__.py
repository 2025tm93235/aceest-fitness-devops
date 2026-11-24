"""ACEest Fitness & Gym - Flask application package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask

from aceest.config import load_config
from aceest.errors import register_error_handlers

__version__ = "1.0.0"


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Application factory.

    ``test_config`` overrides the environment-derived configuration and is
    used by the test-suite to point the app at a temporary database.
    """
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if test_config:
        app.config.from_mapping(test_config)

    register_error_handlers(app)
    _register_version_headers(app)

    from aceest import db

    db.init_app(app)

    from aceest import auth

    auth.init_app(app)

    from aceest import api

    api.init_app(app)

    from aceest import web

    web.init_app(app)
    return app


def _register_version_headers(app: Flask) -> None:
    """Expose the running version and track on every response and template."""

    @app.after_request
    def add_version_headers(response):
        response.headers["X-App-Version"] = __version__
        response.headers["X-Deployment-Track"] = app.config["DEPLOYMENT_TRACK"]
        return response

    @app.context_processor
    def inject_version() -> dict[str, str]:
        return {
            "app_version": __version__,
            "deployment_track": app.config["DEPLOYMENT_TRACK"],
            "instance_name": app.config["INSTANCE_NAME"],
        }
