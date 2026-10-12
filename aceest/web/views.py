"""HTML views: login, dashboard, client pages and program catalogue."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import date
from typing import Any

from flask import flash, redirect, render_template, request, url_for

from aceest import repository
from aceest.auth import current_user, login_required, login_user, logout_user, verify_credentials
from aceest.catalog import PROGRAMS
from aceest.errors import ApiError
from aceest.services import (
    EXPERIENCE_LEVELS,
    WORKOUT_TYPES,
    generate_program,
    membership_state,
)
from aceest.validation import ValidationError, Validator
from aceest.web import bp

# Endpoint names and flash-message categories used by several views
# (one definition each instead of repeated string literals).
DASHBOARD = "web.dashboard"
CLIENT_DETAIL = "web.client_detail"
FLASH_SUCCESS = "success"
FLASH_ERROR = "error"


def flash_errors(error: ValidationError) -> None:
    for field, message in error.errors.items():
        flash(f"{field.replace('_', ' ').capitalize()} {message}.", FLASH_ERROR)


def safe_next(target: str | None) -> str:
    """Only allow same-site relative redirects after login (no open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for(DASHBOARD)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for(DASHBOARD))
        return render_template("login.html", next=request.args.get("next", ""))

    username = request.form.get("username", "").strip()
    role = verify_credentials(username, request.form.get("password", ""))
    if role is None:
        flash("Invalid username or password.", FLASH_ERROR)
        return render_template("login.html", next=request.form.get("next", "")), 401
    login_user(username, role)
    flash(f"Welcome, {username}.", FLASH_SUCCESS)
    return redirect(safe_next(request.form.get("next")))


@bp.post("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", FLASH_SUCCESS)
    return redirect(url_for("web.login"))


@bp.get("/")
@login_required
def dashboard():
    today = date.today()
    clients = repository.list_clients()
    for client in clients:
        client["membership"] = membership_state(
            client["membership_status"], client["membership_end"], today
        )
    return render_template("dashboard.html", clients=clients, programs=PROGRAMS)


@bp.post("/clients")
@login_required
def create_client():
    try:
        client = repository.create_client(request.form)
    except ValidationError as error:
        flash_errors(error)
        return redirect(url_for(DASHBOARD))
    flash(f"Client {client['name']} saved.", FLASH_SUCCESS)
    return redirect(url_for(CLIENT_DETAIL, name=client["name"]))


# ------------------------------------------------------------ client page --
def _client_page(name: str, **extra: Any) -> str:
    summary = repository.client_summary(name)
    try:
        bmi = repository.client_bmi(name)
    except ApiError:
        bmi = None
    return render_template(
        "client.html",
        summary=summary,
        client=summary["client"],
        bmi=bmi,
        membership=repository.client_membership(name),
        progress=repository.list_progress(name),
        metrics=repository.list_metrics(name),
        workouts=repository.list_workouts(name),
        programs=PROGRAMS,
        workout_types=WORKOUT_TYPES,
        experience_levels=EXPERIENCE_LEVELS,
        today=date.today().isoformat(),
        **extra,
    )


def _submit(name: str, action: Callable[[], Any], success: str) -> Any:
    """Run a form action, flash the outcome and redirect back to the client page."""
    try:
        action()
    except ValidationError as error:
        flash_errors(error)
    else:
        flash(success, FLASH_SUCCESS)
    return redirect(url_for(CLIENT_DETAIL, name=name))


@bp.get("/clients/<name>")
@login_required
def client_detail(name: str):
    return _client_page(name)


@bp.post("/clients/<name>/update")
@login_required
def update_client(name: str):
    try:
        client = repository.update_client(name, request.form)
    except ValidationError as error:
        flash_errors(error)
        return redirect(url_for(CLIENT_DETAIL, name=name))
    flash("Profile updated.", FLASH_SUCCESS)
    return redirect(url_for(CLIENT_DETAIL, name=client["name"]))


@bp.post("/clients/<name>/delete")
@login_required
def delete_client(name: str):
    repository.delete_client(name)
    flash(f"Client {name} deleted.", FLASH_SUCCESS)
    return redirect(url_for(DASHBOARD))


@bp.post("/clients/<name>/progress")
@login_required
def add_progress(name: str):
    return _submit(
        name, lambda: repository.add_progress(name, request.form), "Weekly progress logged."
    )


@bp.post("/clients/<name>/metrics")
@login_required
def add_metric(name: str):
    return _submit(name, lambda: repository.add_metric(name, request.form), "Metrics logged.")


def _exercises_from_form(form: Any, rows: int = 3) -> list[dict[str, str]]:
    exercises = []
    for index in range(rows):
        row = {
            field: form.get(f"exercise_{field}_{index}", "")
            for field in ("name", "sets", "reps", "weight")
        }
        if any(value.strip() for value in row.values()):
            exercises.append(row)
    return exercises


@bp.post("/clients/<name>/workouts")
@login_required
def add_workout(name: str):
    payload = {**request.form.to_dict(), "exercises": _exercises_from_form(request.form)}
    return _submit(name, lambda: repository.add_workout(name, payload), "Workout logged.")


@bp.post("/clients/<name>/program")
@login_required
def generate_client_program(name: str):
    client = repository.require_client(name)
    try:
        data = (
            Validator(request.form)
            .string("experience", required=True, choices=EXPERIENCE_LEVELS)
            .integer("seed", minimum=0)
            .validate()
        )
    except ValidationError as error:
        flash_errors(error)
        return redirect(url_for(CLIENT_DETAIL, name=name))
    rng = random.Random(data.get("seed"))  # noqa: S311 - not security-sensitive
    generated = generate_program(client["program"], data["experience"], rng)
    return _client_page(name, generated=generated)


@bp.get("/programs")
def programs():
    return render_template("programs.html", programs=PROGRAMS.values())
