"""Gym-wide statistics (release 1.2.0)."""

from __future__ import annotations

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required


@bp.get("/stats")
@login_required
def gym_stats():
    return jsonify(repository.gym_stats())
