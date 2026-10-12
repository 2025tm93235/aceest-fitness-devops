"""Pure business logic ported from the legacy desktop app.

Functions here have no Flask or database dependencies so they can be unit
tested directly.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from aceest.catalog import get_program

# Validation limits shared by the API and the web forms.
WEIGHT_RANGE_KG = (1.0, 500.0)
HEIGHT_RANGE_CM = (50.0, 272.0)

# Stored membership states (legacy v3.2.4 defaulted every client to "Active").
ACTIVE = "Active"
MEMBERSHIP_STATUSES = (ACTIVE, "Inactive")

# Training focus shared by the workout types and the program generator.
HYPERTROPHY = "Hypertrophy"

# Session types offered by the legacy v2.2.4 "Log Workout" window.
WORKOUT_TYPES = ("Strength", HYPERTROPHY, "Cardio", "Mobility")


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


# ------------------------------------------------------ program generator --
# Exercise pool and experience rules from the legacy v3.1.2 "AI" generator.
EXERCISE_POOL: dict[str, tuple[str, ...]] = {
    "Strength": ("Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"),
    HYPERTROPHY: (
        "Leg Press",
        "Incline Dumbbell Press",
        "Lat Pulldown",
        "Lateral Raise",
        "Bicep Curl",
        "Tricep Extension",
    ),
    "Conditioning": ("Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"),
    "Full Body": ("Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"),
}

EXPERIENCE_LEVELS: dict[str, dict[str, Any]] = {
    "beginner": {"sets": (2, 3), "reps": (8, 12), "days": 3},
    "intermediate": {"sets": (3, 4), "reps": (8, 15), "days": 4},
    "advanced": {"sets": (4, 5), "reps": (6, 15), "days": 5},
}

TRAINING_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


@dataclass(frozen=True)
class GeneratedProgram:
    experience: str
    focus: str
    days_per_week: int
    plan: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def program_focus(program_code: str | None) -> str:
    """Training focus derived from the client's program (legacy v3.1.2 rule)."""
    code = program_code or ""
    if code.startswith("fat-loss"):
        return "Conditioning"
    if code.startswith("muscle-gain"):
        return HYPERTROPHY
    return "Full Body"


def generate_program(
    program_code: str | None, experience: str, rng: random.Random | None = None
) -> GeneratedProgram:
    """Build a weekly plan of exercises, sets and reps.

    ``rng`` is injectable so results are reproducible (pass a seeded
    ``random.Random``); the legacy version used the global random state.
    """
    level = EXPERIENCE_LEVELS.get(experience.lower())
    if level is None:
        raise ValueError(f"Unknown experience level '{experience}'")
    rng = rng or random.Random()  # noqa: S311 - workout variety, not security-sensitive

    focus = program_focus(program_code)
    days = level["days"]
    per_day = 3 if days < 4 else 4
    plan = [
        {
            "day": day,
            "exercise": exercise,
            "sets": rng.randint(*level["sets"]),
            "reps": rng.randint(*level["reps"]),
        }
        for day in TRAINING_DAYS[:days]
        for exercise in rng.sample(EXERCISE_POOL[focus], k=per_day)
    ]
    return GeneratedProgram(experience.lower(), focus, days, plan)


# ------------------------------------------------------------- membership --
def membership_state(status: str, membership_end: str | None, today: date) -> dict[str, Any]:
    """Effective membership status (legacy v3.2.4 'Check Membership').

    An "Active" membership whose end date has passed is reported as "Expired".
    """
    end = date.fromisoformat(membership_end) if membership_end else None
    days_remaining = (end - today).days if end else None
    if status != ACTIVE:
        effective = status
    elif end is not None and end < today:
        effective = "Expired"
    else:
        effective = ACTIVE
    return {
        "status": status,
        "effective_status": effective,
        "membership_end": membership_end,
        "days_remaining": days_remaining,
        "is_active": effective == ACTIVE,
    }
