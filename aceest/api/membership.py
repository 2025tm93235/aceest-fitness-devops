"""Membership status check (legacy v3.2.4)."""

from __future__ import annotations

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required


@bp.get("/clients/<name>/membership")
@login_required
def client_membership(name: str):
    return jsonify(repository.client_membership(name))
