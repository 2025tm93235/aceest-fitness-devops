"""Stand-alone calculators (legacy v1.1 calories, v2.2.4 BMI)."""

from __future__ import annotations

from flask import jsonify

from aceest.api import bp
from aceest.catalog import PROGRAMS, get_program
from aceest.services import HEIGHT_RANGE_CM, WEIGHT_RANGE_KG, calculate_bmi, estimate_calories
from aceest.validation import Validator, json_body


@bp.post("/calculators/calories")
def calories():
    data = (
        Validator(json_body())
        .number("weight", required=True, minimum=WEIGHT_RANGE_KG[0], maximum=WEIGHT_RANGE_KG[1])
        .string("program", required=True, choices=PROGRAMS)
        .validate()
    )
    program = get_program(data["program"])
    return jsonify(
        program=program.code,
        weight=data["weight"],
        calorie_factor=program.calorie_factor,
        calories=estimate_calories(data["weight"], program.code),
    )


@bp.post("/calculators/bmi")
def bmi():
    data = (
        Validator(json_body())
        .number("height", required=True, minimum=HEIGHT_RANGE_CM[0], maximum=HEIGHT_RANGE_CM[1])
        .number("weight", required=True, minimum=WEIGHT_RANGE_KG[0], maximum=WEIGHT_RANGE_KG[1])
        .validate()
    )
    return jsonify(calculate_bmi(data["height"], data["weight"]).to_dict())
