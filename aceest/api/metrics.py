"""Body metrics and client BMI (legacy v2.2.4 / v3.0.1)."""

from __future__ import annotations

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required
from aceest.validation import json_body


@bp.get("/clients/<name>/metrics")
@login_required
def list_metrics(name: str):
    return jsonify(metrics=repository.list_metrics(name))


@bp.post("/clients/<name>/metrics")
@login_required
def add_metric(name: str):
    return jsonify(repository.add_metric(name, json_body())), 201


@bp.get("/clients/<name>/bmi")
@login_required
def client_bmi(name: str):
    return jsonify({"client": name, **repository.client_bmi(name).to_dict()})
