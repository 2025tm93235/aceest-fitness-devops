"""Training program catalogue.

Program names, calorie factors and descriptions come from legacy v2.2.4;
the weekly workout and nutrition plans come from legacy v1.0/v1.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Program:
    code: str
    name: str
    calorie_factor: int
    description: str
    workout: tuple[str, ...]
    diet: tuple[str, ...]
    color: str

    def summary(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "calorie_factor": self.calorie_factor,
            "description": self.description,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "workout": list(self.workout),
            "diet": list(self.diet),
            "color": self.color,
        }


_FAT_LOSS_DIET = (
    "Breakfast: Egg Whites + Oats",
    "Lunch: Grilled Chicken + Brown Rice",
    "Dinner: Fish Curry + Millet Roti",
    "Target: ~2000 kcal",
)

PROGRAMS: dict[str, Program] = {
    program.code: program
    for program in (
        Program(
            code="fat-loss-3day",
            name="Fat Loss (FL) - 3 day",
            calorie_factor=22,
            description="3-day full-body fat loss",
            workout=(),  # the baseline defines no day-by-day plan for this variant
            diet=_FAT_LOSS_DIET,
            color="#e74c3c",
        ),
        Program(
            code="fat-loss-5day",
            name="Fat Loss (FL) - 5 day",
            calorie_factor=24,
            description="5-day split, higher volume fat loss",
            workout=(
                "Mon: Back Squat 5x5 + Core",
                "Tue: EMOM 20min Assault Bike",
                "Wed: Bench Press + 21-15-9",
                "Thu: Deadlift + Box Jumps",
                "Fri: Zone 2 Cardio 30min",
            ),
            diet=_FAT_LOSS_DIET,
            color="#e74c3c",
        ),
        Program(
            code="muscle-gain-ppl",
            name="Muscle Gain (MG) - PPL",
            calorie_factor=35,
            description="Push/Pull/Legs hypertrophy",
            workout=(
                "Mon: Squat 5x5",
                "Tue: Bench 5x5",
                "Wed: Deadlift 4x6",
                "Thu: Front Squat 4x8",
                "Fri: Incline Press 4x10",
                "Sat: Barbell Rows 4x10",
            ),
            diet=(
                "Breakfast: Eggs + Peanut Butter Oats",
                "Lunch: Chicken Biryani",
                "Dinner: Mutton Curry + Rice",
                "Target: ~3200 kcal",
            ),
            color="#2ecc71",
        ),
        Program(
            code="beginner",
            name="Beginner (BG)",
            calorie_factor=26,
            description="3-day simple beginner full-body",
            workout=(
                "Full Body Circuit: Air Squats, Ring Rows, Push-ups",
                "Focus: Technique & Consistency",
            ),
            diet=(
                "Balanced Tamil Meals",
                "Idli / Dosa / Rice + Dal",
                "Protein Target: 120g/day",
            ),
            color="#3498db",
        ),
    )
}


def get_program(code: str) -> Program | None:
    return PROGRAMS.get(code)
