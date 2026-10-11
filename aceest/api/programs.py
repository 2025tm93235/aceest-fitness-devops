"""Program catalogue endpoints (legacy v1.0 / v2.2.4)."""

from __future__ import annotations

from flask import jsonify

from aceest.api import bp
from aceest.catalog import PROGRAMS, get_program
from aceest.errors import ApiError


@bp.get("/programs")
def list_programs():
    return jsonify(programs=[program.summary() for program in PROGRAMS.values()])


@bp.get("/programs/<code>")
def program_detail(code: str):
    program = get_program(code)
    if program is None:
        raise ApiError(f"Program '{code}' not found", status=404)
    return jsonify(program.to_dict())
