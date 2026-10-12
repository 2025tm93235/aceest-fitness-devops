"""Data access for clients and their related records."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import date
from typing import Any

from aceest.catalog import PROGRAMS, get_program
from aceest.db import get_db
from aceest.errors import ApiError
from aceest.services import (
    HEIGHT_RANGE_CM,
    WEIGHT_RANGE_KG,
    WORKOUT_TYPES,
    estimate_calories,
    week_label,
)
from aceest.validation import ValidationError, Validator

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


# --------------------------------------------------------------- progress --
def add_progress(name: str, data: Mapping[str, Any]) -> dict[str, Any]:
    client = require_client(name)
    entry = (
        Validator(data)
        .integer("adherence", required=True, minimum=0, maximum=100)
        .string("week", max_length=20, default=week_label(date.today()))
        .validate()
    )
    db = get_db()
    cursor = db.execute(
        "INSERT INTO progress (client_id, week, adherence) VALUES (?, ?, ?)",
        (client["id"], entry["week"], entry["adherence"]),
    )
    db.commit()
    row = db.execute(
        "SELECT id, week, adherence, recorded_at FROM progress WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


def list_progress(name: str) -> list[dict[str, Any]]:
    client = require_client(name)
    rows = get_db().execute(
        "SELECT id, week, adherence, recorded_at FROM progress WHERE client_id = ? ORDER BY id",
        (client["id"],),
    )
    return [dict(row) for row in rows]


# --------------------------------------------------------------- workouts --
def _validate_exercises(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationError({"exercises": "must be a list"})
    exercises: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            errors[f"exercises[{index}]"] = "must be an object"
            continue
        try:
            exercises.append(
                Validator(item)
                .string("name", required=True, max_length=80)
                .integer("sets", minimum=1, maximum=20)
                .integer("reps", minimum=1, maximum=100)
                .number("weight", minimum=0, maximum=1000)
                .validate()
            )
        except ValidationError as exc:
            errors.update({f"exercises[{index}].{k}": v for k, v in exc.errors.items()})
    if errors:
        raise ValidationError(errors)
    return exercises


def add_workout(name: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Log a workout session with its exercises in a single transaction."""
    client = require_client(name)
    workout = (
        Validator(data)
        .date("date", default=date.today().isoformat())
        .string("workout_type", required=True, choices=WORKOUT_TYPES)
        .integer("duration_min", minimum=1, maximum=600, default=60)
        .string("notes", max_length=500)
        .validate()
    )
    exercises = _validate_exercises(data.get("exercises"))

    db = get_db()
    with db:  # commit on success, roll back on error
        cursor = db.execute(
            "INSERT INTO workouts (client_id, date, workout_type, duration_min, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                client["id"],
                workout["date"],
                workout["workout_type"],
                workout["duration_min"],
                workout.get("notes"),
            ),
        )
        workout_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
            [
                (workout_id, e["name"], e.get("sets"), e.get("reps"), e.get("weight"))
                for e in exercises
            ],
        )
    return _load_workout(workout_id)


def _load_workout(workout_id: int) -> dict[str, Any]:
    db = get_db()
    workout = dict(
        db.execute(
            "SELECT id, date, workout_type, duration_min, notes FROM workouts WHERE id = ?",
            (workout_id,),
        ).fetchone()
    )
    workout["exercises"] = [
        dict(row)
        for row in db.execute(
            "SELECT name, sets, reps, weight FROM exercises WHERE workout_id = ? ORDER BY id",
            (workout_id,),
        )
    ]
    return workout


def list_workouts(name: str) -> list[dict[str, Any]]:
    """Workout history, newest first (legacy v2.2.4 history window)."""
    client = require_client(name)
    ids = get_db().execute(
        "SELECT id FROM workouts WHERE client_id = ? ORDER BY date DESC, id DESC", (client["id"],)
    )
    return [_load_workout(row["id"]) for row in ids.fetchall()]


# ---------------------------------------------------------------- summary --
def client_summary(name: str) -> dict[str, Any]:
    """Profile, program notes, goals and progress statistics (legacy v2.2.4)."""
    client = require_client(name)
    db = get_db()
    weeks_logged, average = db.execute(
        "SELECT COUNT(*), AVG(adherence) FROM progress WHERE client_id = ?", (client["id"],)
    ).fetchone()
    program = get_program(client["program"]) if client["program"] else None
    return {
        "client": client,
        "program": program.summary() if program else None,
        "goals": {
            "target_weight": client["target_weight"],
            "target_adherence": client["target_adherence"],
        },
        "progress": {
            "weeks_logged": weeks_logged,
            "average_adherence": round(average, 1) if average is not None else 0,
        },
    }
