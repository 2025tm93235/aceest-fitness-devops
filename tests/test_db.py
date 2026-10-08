"""Database initialisation and connection lifecycle."""

from __future__ import annotations

from aceest.db import get_db, init_db

EXPECTED_TABLES = {"users", "clients", "progress", "workouts", "exercises", "metrics"}


def _tables(app) -> set[str]:
    with app.app_context():
        rows = get_db().execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_schema_is_created_on_startup(app):
    assert _tables(app) >= EXPECTED_TABLES


def test_init_db_is_idempotent_and_keeps_data(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO clients (name) VALUES ('Arun')")
        db.commit()
        init_db()
        init_db()
        count = db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    assert count == 1


def test_connection_is_reused_within_context_and_closed_after(app):
    with app.app_context():
        first = get_db()
        assert get_db() is first
    # A new context gets a new connection
    with app.app_context():
        assert get_db() is not first


def test_foreign_keys_are_enforced(app):
    with app.app_context():
        enabled = get_db().execute("PRAGMA foreign_keys").fetchone()[0]
    assert enabled == 1


def test_database_directory_is_created(tmp_path):
    from aceest import create_app

    target = tmp_path / "nested" / "dir" / "aceest.db"
    create_app({"TESTING": True, "DATABASE": str(target)})
    assert target.exists()


def test_init_db_cli_command(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "up to date" in result.output


def test_health_reports_database_ok(client):
    body = client.get("/health").get_json()
    assert body["database"] == "ok"


def test_health_reports_degraded_when_database_unavailable(app, tmp_path):
    # Point the running app at a directory: SQLite cannot open it.
    app.config["DATABASE"] = str(tmp_path)
    response = app.test_client().get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "degraded"
