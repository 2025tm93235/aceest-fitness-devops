"""Unit tests for the input Validator."""

from __future__ import annotations

import pytest

from aceest.validation import ValidationError, Validator


def _errors(validator: Validator) -> dict[str, str]:
    with pytest.raises(ValidationError) as excinfo:
        validator.validate()
    return excinfo.value.errors


def test_string_is_trimmed_and_validated():
    data = Validator({"name": "  Arun  "}).string("name", required=True).validate()
    assert data == {"name": "Arun"}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (123, "must be a string"),
        ("x" * 6, "must be at most 5 characters"),
    ],
)
def test_string_errors(value, message):
    assert _errors(Validator({"s": value}).string("s", max_length=5)) == {"s": message}


def test_string_choices():
    assert Validator({"c": "b"}).string("c", choices=["a", "b"]).validate() == {"c": "b"}
    assert _errors(Validator({"c": "z"}).string("c", choices=["a", "b"])) == {
        "c": "must be one of: a, b"
    }


def test_missing_optional_field_is_skipped_but_blank_clears_value():
    assert Validator({}).string("note").validate() == {}
    assert Validator({"note": "  "}).string("note").validate() == {"note": None}
    assert Validator({"note": None}).integer("note").validate() == {"note": None}


def test_required_field_missing():
    assert _errors(Validator({}).integer("age", required=True)) == {"age": "is required"}


def test_defaults_are_applied():
    data = Validator({}).integer("n", default=60).string("s", default="x").validate()
    assert data == {"n": 60, "s": "x"}


@pytest.mark.parametrize(("raw", "expected"), [(5, 5), ("7", 7), (8.0, 8), (" 9 ", 9)])
def test_integer_accepts_numeric_input(raw, expected):
    assert Validator({"n": raw}).integer("n").validate() == {"n": expected}


@pytest.mark.parametrize("raw", ["abc", 2.5, True, [1], "nan", float("inf")])
def test_integer_rejects_invalid_input(raw):
    assert _errors(Validator({"n": raw}).integer("n")) == {"n": "must be a whole number"}


def test_integer_range():
    assert _errors(Validator({"n": 0}).integer("n", minimum=1)) == {"n": "must be at least 1"}
    assert _errors(Validator({"n": 101}).integer("n", maximum=100)) == {"n": "must be at most 100"}


def test_number_parses_and_checks_range():
    assert Validator({"w": "72.5"}).number("w", minimum=1).validate() == {"w": 72.5}
    assert _errors(Validator({"w": "heavy"}).number("w")) == {"w": "must be a number"}
    assert _errors(Validator({"w": 0}).number("w", minimum=1)) == {"w": "must be at least 1"}


def test_date_is_normalised():
    assert Validator({"d": "2026-01-05"}).date("d").validate() == {"d": "2026-01-05"}
    assert _errors(Validator({"d": "05/01/2026"}).date("d")) == {
        "d": "must be a date in YYYY-MM-DD format"
    }
    assert Validator({}).date("d", default="2026-02-01").validate() == {"d": "2026-02-01"}


def test_all_errors_are_reported_together():
    errors = _errors(
        Validator({"a": "x", "b": "y"}).integer("a").number("b").string("c", required=True)
    )
    assert set(errors) == {"a", "b", "c"}


def test_validation_error_maps_to_http_400():
    error = ValidationError({"f": "bad"})
    assert error.status == 400
    assert error.to_dict() == {"error": "Validation failed", "details": {"f": "bad"}}
