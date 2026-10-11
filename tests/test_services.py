"""Unit tests for the pure business logic in aceest.services."""

from __future__ import annotations

import pytest

from aceest.services import calculate_bmi, estimate_calories


@pytest.mark.parametrize(
    ("weight", "program", "expected"),
    [
        (70, "fat-loss-3day", 1540),
        (70, "fat-loss-5day", 1680),
        (80, "muscle-gain-ppl", 2800),
        (60, "beginner", 1560),
        (72.5, "beginner", 1885),  # truncated like the legacy int() conversion
    ],
)
def test_estimate_calories(weight, program, expected):
    assert estimate_calories(weight, program) == expected


def test_estimate_calories_rejects_unknown_program():
    with pytest.raises(ValueError, match="Unknown program"):
        estimate_calories(70, "keto")


def test_estimate_calories_rejects_non_positive_weight():
    with pytest.raises(ValueError, match="positive"):
        estimate_calories(0, "beginner")


@pytest.mark.parametrize(
    ("height", "weight", "bmi", "category"),
    [
        (180, 55, 17.0, "Underweight"),
        (170, 53.4, 18.5, "Normal"),  # lower boundary is Normal
        (175, 70, 22.9, "Normal"),
        (170, 72.2, 25.0, "Overweight"),  # 25.0 is Overweight
        (170, 86.7, 30.0, "Obese"),  # 30.0 is Obese
        (160, 100, 39.1, "Obese"),
    ],
)
def test_calculate_bmi_categories(height, weight, bmi, category):
    result = calculate_bmi(height, weight)
    assert result.bmi == bmi
    assert result.category == category
    assert result.risk


def test_calculate_bmi_to_dict():
    assert set(calculate_bmi(175, 70).to_dict()) == {"bmi", "category", "risk"}


@pytest.mark.parametrize(("height", "weight"), [(0, 70), (170, 0), (-1, 70)])
def test_calculate_bmi_rejects_invalid_input(height, weight):
    with pytest.raises(ValueError):
        calculate_bmi(height, weight)
