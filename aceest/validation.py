"""Input validation shared by the JSON API and the HTML forms."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

from flask import request

from aceest.errors import ApiError


class ValidationError(ApiError):
    """Raised when one or more input fields are invalid (HTTP 400)."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed", status=400, details=errors)
        self.errors = errors


def json_body() -> dict[str, Any]:
    """Return the request JSON body, which must be an object."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", status=400)
    return data


class Validator:
    """Validate and normalise a mapping of raw input values.

    * A field that is absent is skipped (supports partial updates) unless it
      is required or has a default.
    * A field that is present but empty (``None`` or blank string) is stored
      as ``None`` so optional values can be cleared.
    * All errors are collected and raised together by :meth:`validate`.
    """

    def __init__(self, data: Mapping[str, Any]) -> None:
        self.data = data
        self.errors: dict[str, str] = {}
        self.cleaned: dict[str, Any] = {}

    # ------------------------------------------------------------ helpers --
    def _raw(self, field: str, required: bool, default: Any) -> tuple[bool, Any]:
        """Return ``(should_process, value)`` for ``field``."""
        if field not in self.data or _is_blank(self.data[field]):
            if default is not None:
                self.cleaned[field] = default
                return False, None
            if required:
                self.errors[field] = "is required"
                return False, None
            if field in self.data:
                self.cleaned[field] = None
            return False, None
        return True, self.data[field]

    def _check_range(
        self, field: str, value: float, minimum: float | None, maximum: float | None
    ) -> bool:
        if minimum is not None and value < minimum:
            self.errors[field] = f"must be at least {minimum}"
            return False
        if maximum is not None and value > maximum:
            self.errors[field] = f"must be at most {maximum}"
            return False
        return True

    # ------------------------------------------------------------- fields --
    def string(
        self,
        field: str,
        *,
        required: bool = False,
        max_length: int = 100,
        choices: Iterable[str] | None = None,
        default: str | None = None,
    ) -> Validator:
        process, value = self._raw(field, required, default)
        if not process:
            return self
        if not isinstance(value, str):
            self.errors[field] = "must be a string"
            return self
        value = value.strip()
        if len(value) > max_length:
            self.errors[field] = f"must be at most {max_length} characters"
            return self
        if choices is not None:
            allowed = list(choices)
            if value not in allowed:
                self.errors[field] = f"must be one of: {', '.join(allowed)}"
                return self
        self.cleaned[field] = value
        return self

    def integer(
        self,
        field: str,
        *,
        required: bool = False,
        minimum: int | None = None,
        maximum: int | None = None,
        default: int | None = None,
    ) -> Validator:
        process, value = self._raw(field, required, default)
        if not process:
            return self
        number = _to_number(value)
        if number is None or not float(number).is_integer():
            self.errors[field] = "must be a whole number"
            return self
        number = int(number)
        if self._check_range(field, number, minimum, maximum):
            self.cleaned[field] = number
        return self

    def number(
        self,
        field: str,
        *,
        required: bool = False,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> Validator:
        process, value = self._raw(field, required, None)
        if not process:
            return self
        number = _to_number(value)
        if number is None:
            self.errors[field] = "must be a number"
            return self
        if self._check_range(field, number, minimum, maximum):
            self.cleaned[field] = float(number)
        return self

    def date(self, field: str, *, required: bool = False, default: str | None = None) -> Validator:
        process, value = self._raw(field, required, default)
        if not process:
            return self
        try:
            self.cleaned[field] = date.fromisoformat(str(value).strip()).isoformat()
        except ValueError:
            self.errors[field] = "must be a date in YYYY-MM-DD format"
        return self

    def validate(self) -> dict[str, Any]:
        if self.errors:
            raise ValidationError(self.errors)
        return self.cleaned


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _to_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = value
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if isinstance(number, float) and not math.isfinite(number):
        return None
    return number
