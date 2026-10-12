"""Pure business logic ported from the legacy desktop app.

Functions here have no Flask or database dependencies so they can be unit
tested directly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from aceest.catalog import get_program

# Validation limits shared by the API and the web forms.
WEIGHT_RANGE_KG = (1.0, 500.0)
HEIGHT_RANGE_CM = (50.0, 272.0)

# Session types offered by the legacy v2.2.4 "Log Workout" window.
WORKOUT_TYPES = ("Strength", "Hypertrophy", "Cardio", "Mobility")


def estimate_calories(weight_kg: float, program_code: str) -> int:
    """Daily calorie estimate = body weight x program factor (legacy v1.1)."""
    program = get_program(program_code)
    if program is None:
        raise ValueError(f"Unknown program '{program_code}'")
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    return int(weight_kg * program.calorie_factor)


@dataclass(frozen=True)
class BmiResult:
    bmi: float
    category: str
    risk: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_bmi(height_cm: float, weight_kg: float) -> BmiResult:
    """Body-mass index with the legacy v2.2.4 categories and risk notes."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive")

    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)

    if bmi < 18.5:
        return BmiResult(bmi, "Underweight", "Potential nutrient deficiency, low energy.")
    if bmi < 25:
        return BmiResult(bmi, "Normal", "Low risk if active and strong.")
    if bmi < 30:
        return BmiResult(
            bmi, "Overweight", "Moderate risk; focus on adherence and progressive activity."
        )
    return BmiResult(
        bmi, "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."
    )


def week_label(day: date) -> str:
    """Label used for weekly adherence entries, e.g. ``Week 07 - 2026`` (legacy v2.0)."""
    return day.strftime("Week %U - %Y")
