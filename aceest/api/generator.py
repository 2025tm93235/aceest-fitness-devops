"""Rule-based workout program generator (legacy v3.1.2 'AI program')."""

from __future__ import annotations

import random

from flask import jsonify

from aceest import repository
from aceest.api import bp
from aceest.auth import login_required
from aceest.services import EXPERIENCE_LEVELS, generate_program
from aceest.validation import Validator, json_body


@bp.post("/clients/<name>/program")
@login_required
def generate_client_program(name: str):
    client = repository.require_client(name)
    data = (
        Validator(json_body())
        .string("experience", required=True, choices=EXPERIENCE_LEVELS)
        .integer("seed", minimum=0)
        .validate()
    )
    rng = random.Random(data.get("seed"))  # noqa: S311 - not security-sensitive
    program = generate_program(client["program"], data["experience"], rng)
    return jsonify({"client": client["name"], "program": client["program"], **program.to_dict()})
