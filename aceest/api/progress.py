"""Weekly adherence tracking and client summary (legacy v2.0 - v2.2.4)."""

from __future__ import annotations

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required
from aceest.validation import json_body


@bp.get("/clients/<name>/progress")
@login_required
def list_progress(name: str):
    return jsonify(progress=repository.list_progress(name))


@bp.post("/clients/<name>/progress")
@login_required
def add_progress(name: str):
    return jsonify(repository.add_progress(name, json_body())), 201


@bp.get("/clients/<name>/summary")
@login_required
def client_summary(name: str):
    return jsonify(repository.client_summary(name))
