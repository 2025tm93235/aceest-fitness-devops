"""Liveness endpoint used by Docker HEALTHCHECK, Jenkins and CI smoke tests."""

from __future__ import annotations

import sqlite3

from flask import Blueprint, current_app, jsonify

import aceest
from aceest.db import get_db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        database = "ok"
    except sqlite3.Error:
        database = "unavailable"

    healthy = database == "ok"
    body = {
        "status": "ok" if healthy else "degraded",
        "service": "aceest-fitness",
        "version": aceest.__version__,
        "database": database,
    }
    return jsonify(body), 200 if healthy else 503


@bp.get("/version")
def version():
    """Which version, deployment track and pod answered this request."""
    return jsonify(
        version=aceest.__version__,
        track=current_app.config["DEPLOYMENT_TRACK"],
        instance=current_app.config["INSTANCE_NAME"],
    )
