"""Database migrations manager for Forecast Fusion SQLite repository."""

import logging
import sqlite3

_LOGGER = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

MIGRATION_V1_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    forecast_type TEXT NOT NULL,
    raw_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forecast_points (
    point_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    forecast_type TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    issued_at TEXT,
    valid_at TEXT NOT NULL,
    lead_time_seconds REAL NOT NULL,
    temperature_c REAL,
    apparent_temperature_c REAL,
    dew_point_c REAL,
    humidity_pct REAL,
    pressure_hpa REAL,
    precipitation_probability_pct REAL,
    precipitation_mm REAL,
    snow_mm REAL,
    wind_speed_ms REAL,
    wind_gust_ms REAL,
    wind_bearing_deg REAL,
    cloud_cover_pct REAL,
    uv_index REAL,
    condition TEXT,
    raw_hash TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    parameter TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT,
    source_mode TEXT NOT NULL,
    source_entity_id TEXT,
    quality TEXT NOT NULL,
    entered_at TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS verification_results (
    verification_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    parameter TEXT NOT NULL,
    lead_time_bucket TEXT NOT NULL,
    valid_at TEXT NOT NULL,
    forecast_value TEXT NOT NULL,
    observed_value TEXT NOT NULL,
    error REAL,
    abs_error REAL,
    brier_score REAL,
    stability_delta REAL,
    correction_benefit REAL,
    verified_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_forecast_points_source_valid
    ON forecast_points(source_id, valid_at);

CREATE INDEX IF NOT EXISTS idx_forecast_points_valid
    ON forecast_points(valid_at);

CREATE INDEX IF NOT EXISTS idx_observations_param_start
    ON observations(parameter, start_at);

CREATE INDEX IF NOT EXISTS idx_verification_source_param_bucket
    ON verification_results(source_id, parameter, lead_time_bucket);
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply all idempotent migrations up to CURRENT_SCHEMA_VERSION."""
    conn.execute("PRAGMA foreign_keys = ON;")

    # Check current version
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(version) FROM schema_version;")
        row = cursor.fetchone()
        current = row[0] if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        current = 0

    if current < 1:
        _LOGGER.info("Applying Forecast Fusion database migration v1")
        cursor.executescript(MIGRATION_V1_SQL)
        cursor.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));"
        )
        conn.commit()
