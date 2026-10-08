"""Liveness endpoint used by Docker HEALTHCHECK, Jenkins and CI smoke tests."""

from __future__ import annotations

from flask import Blueprint, jsonify

import aceest

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", service="aceest-fitness", version=aceest.__version__)
