-- ACEest Fitness & Gym data model.
-- Ported from the baseline SQLite schema (legacy v2.0 - v3.2.4) with:
--   * foreign keys to clients.id instead of free-text client names
--   * CHECK constraints for ranges
--   * idempotent "IF NOT EXISTS" DDL only - tables are never dropped.

CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'Trainer'
);

CREATE TABLE IF NOT EXISTS clients (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL UNIQUE,
    age               INTEGER CHECK (age IS NULL OR age BETWEEN 1 AND 120),
    height            REAL    CHECK (height IS NULL OR height > 0),
    weight            REAL    CHECK (weight IS NULL OR weight > 0),
    program           TEXT,
    calories          INTEGER,
    target_weight     REAL,
    target_adherence  INTEGER CHECK (target_adherence IS NULL OR target_adherence BETWEEN 0 AND 100),
    membership_status TEXT    NOT NULL DEFAULT 'Active',
    membership_end    TEXT,
    created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    week        TEXT    NOT NULL,
    adherence   INTEGER NOT NULL CHECK (adherence BETWEEN 0 AND 100),
    recorded_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id    INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    date         TEXT    NOT NULL,
    workout_type TEXT    NOT NULL,
    duration_min INTEGER CHECK (duration_min IS NULL OR duration_min > 0),
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts (id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    sets       INTEGER,
    reps       INTEGER,
    weight     REAL
);

CREATE TABLE IF NOT EXISTS metrics (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
    date      TEXT    NOT NULL,
    weight    REAL,
    waist     REAL,
    bodyfat   REAL
);

CREATE INDEX IF NOT EXISTS idx_progress_client  ON progress (client_id);
CREATE INDEX IF NOT EXISTS idx_workouts_client  ON workouts (client_id);
CREATE INDEX IF NOT EXISTS idx_exercises_workout ON exercises (workout_id);
CREATE INDEX IF NOT EXISTS idx_metrics_client   ON metrics (client_id);
