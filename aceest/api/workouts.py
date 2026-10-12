"""Workout session logging with exercises (legacy v2.2.4)."""

from __future__ import annotations

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required
from aceest.validation import json_body


@bp.get("/clients/<name>/workouts")
@login_required
def list_workouts(name: str):
    return jsonify(workouts=repository.list_workouts(name))


@bp.post("/clients/<name>/workouts")
@login_required
def add_workout(name: str):
    return jsonify(repository.add_workout(name, json_body())), 201
