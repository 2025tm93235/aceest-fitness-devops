"""Data access for clients and their related records."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from aceest.catalog import PROGRAMS
from aceest.db import get_db
from aceest.errors import ApiError
from aceest.services import HEIGHT_RANGE_CM, WEIGHT_RANGE_KG, estimate_calories
from aceest.validation import Validator

_UPDATABLE_COLUMNS = (
    "name",
    "age",
    "height",
    "weight",
    "program",
    "calories",
    "target_weight",
    "target_adherence",
)


# ---------------------------------------------------------------- clients --
def validate_client(data: Mapping[str, Any], *, partial: bool = False) -> dict[str, Any]:
    return (
        Validator(data)
        .string("name", required=not partial, max_length=80)
        .integer("age", minimum=1, maximum=120)
        .number("height", minimum=HEIGHT_RANGE_CM[0], maximum=HEIGHT_RANGE_CM[1])
        .number("weight", minimum=WEIGHT_RANGE_KG[0], maximum=WEIGHT_RANGE_KG[1])
        .string("program", choices=PROGRAMS)
        .number("target_weight", minimum=WEIGHT_RANGE_KG[0], maximum=WEIGHT_RANGE_KG[1])
        .integer("target_adherence", minimum=0, maximum=100)
        .validate()
    )


def _with_calories(client: dict[str, Any]) -> dict[str, Any]:
    weight, program = client.get("weight"), client.get("program")
    client["calories"] = estimate_calories(weight, program) if weight and program else None
    return client


def list_clients() -> list[dict[str, Any]]:
    rows = get_db().execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE").fetchall()
    return [dict(row) for row in rows]


def get_client(name: str) -> dict[str, Any] | None:
    row = get_db().execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def require_client(name: str) -> dict[str, Any]:
    client = get_client(name)
    if client is None:
        raise ApiError(f"Client '{name}' not found", status=404)
    return client


def create_client(data: Mapping[str, Any]) -> dict[str, Any]:
    client = _with_calories(validate_client(data))
    columns = [column for column in _UPDATABLE_COLUMNS if column in client]
    placeholders = ", ".join("?" for _ in columns)
    db = get_db()
    try:
        db.execute(
            f"INSERT INTO clients ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608 - column names are a fixed allow-list
            [client[column] for column in columns],
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ApiError(f"Client '{client['name']}' already exists", status=409) from exc
    return require_client(client["name"])


def update_client(name: str, data: Mapping[str, Any]) -> dict[str, Any]:
    existing = require_client(name)
    changes = validate_client(data, partial=True)
    if "name" in changes and changes["name"] is None:
        raise ApiError("Validation failed", status=400, details={"name": "is required"})
    merged = _with_calories({**existing, **changes})

    assignments = ", ".join(f"{column} = ?" for column in _UPDATABLE_COLUMNS)
    db = get_db()
    try:
        db.execute(
            f"UPDATE clients SET {assignments} WHERE id = ?",  # noqa: S608 - fixed allow-list
            [merged[column] for column in _UPDATABLE_COLUMNS] + [existing["id"]],
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ApiError(f"Client '{merged['name']}' already exists", status=409) from exc
    return require_client(merged["name"])


def delete_client(name: str) -> None:
    client = require_client(name)
    db = get_db()
    db.execute("DELETE FROM clients WHERE id = ?", (client["id"],))
    db.commit()
