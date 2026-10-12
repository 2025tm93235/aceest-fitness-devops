"""HTML views: login, dashboard, client creation and program catalogue."""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for

from aceest import repository
from aceest.auth import current_user, login_required, login_user, logout_user, verify_credentials
from aceest.catalog import PROGRAMS
from aceest.services import membership_state
from aceest.validation import ValidationError
from aceest.web import bp


def flash_errors(error: ValidationError) -> None:
    for field, message in error.errors.items():
        flash(f"{field.replace('_', ' ').capitalize()} {message}.", "error")


def safe_next(target: str | None) -> str:
    """Only allow same-site relative redirects after login (no open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("web.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("web.dashboard"))
        return render_template("login.html", next=request.args.get("next", ""))

    username = request.form.get("username", "").strip()
    role = verify_credentials(username, request.form.get("password", ""))
    if role is None:
        flash("Invalid username or password.", "error")
        return render_template("login.html", next=request.form.get("next", "")), 401
    login_user(username, role)
    flash(f"Welcome, {username}.", "success")
    return redirect(safe_next(request.form.get("next")))


@bp.post("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
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
        return redirect(url_for("web.dashboard"))
    flash(f"Client {client['name']} saved.", "success")
    return redirect(url_for("web.dashboard"))


@bp.get("/programs")
def programs():
    return render_template("programs.html", programs=PROGRAMS.values())
