"""Client management endpoints (legacy v1.1 - v2.2.4)."""

from __future__ import annotations

from flask import jsonify, url_for

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required
from aceest.validation import json_body


@bp.get("/clients")
@login_required
def list_clients():
    return jsonify(clients=repository.list_clients())


@bp.post("/clients")
@login_required
def create_client():
    client = repository.create_client(json_body())
    location = url_for("api.get_client", name=client["name"])
    return jsonify(client), 201, {"Location": location}


@bp.get("/clients/<name>")
@login_required
def get_client(name: str):
    return jsonify(repository.require_client(name))


@bp.route("/clients/<name>", methods=["PUT", "PATCH"])
@login_required
def update_client(name: str):
    return jsonify(repository.update_client(name, json_body()))


@bp.delete("/clients/<name>")
@login_required
def delete_client(name: str):
    repository.delete_client(name)
    return "", 204
