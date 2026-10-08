"""SQLite connection handling and schema initialisation."""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext


def get_db() -> sqlite3.Connection:
    """Return the request-scoped database connection, opening it on first use."""
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create any missing tables. Safe to run repeatedly; never drops data."""
    schema = resources.files("aceest").joinpath("schema.sql").read_text(encoding="utf-8")
    db = get_db()
    db.executescript(schema)
    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Create the database schema (idempotent)."""
    init_db()
    click.echo("Database schema is up to date.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()
