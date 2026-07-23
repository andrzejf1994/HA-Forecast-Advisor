"""SQLite repository implementation for Forecast Fusion storage."""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from ..core.enums import ForecastType, ObservationQuality, ObservationSourceMode, WeatherParameter
from ..core.models import (
    ForecastPoint,
    ForecastSnapshot,
    Observation,
    VerificationResult,
)
from ..core.normalizer import ensure_utc
from .migrations import apply_migrations

_LOGGER = logging.getLogger(__name__)


class SQLiteRepository:
    """SQLite implementation of storage repositories."""

    def __init__(self, db_path: str) -> None:
        """Initialize repository with database path."""
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        apply_migrations(conn)
        return conn

    async def async_init(self) -> None:
        """Run database migrations in thread pool."""

        def _init() -> None:
            conn = self._get_connection()
            conn.close()

        await asyncio.to_thread(_init)

    async def save_snapshot(self, snapshot: ForecastSnapshot) -> None:
        """Save a forecast snapshot and its points to SQLite."""

        def _do_save() -> None:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO snapshots
                        (snapshot_id, source_id, fetched_at, forecast_type, raw_hash)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (
                            snapshot.snapshot_id,
                            snapshot.source_id,
                            snapshot.fetched_at.isoformat(),
                            snapshot.forecast_type.value,
                            snapshot.raw_hash,
                        ),
                    )

                    for idx, p in enumerate(snapshot.points):
                        point_id = f"{snapshot.snapshot_id}_{idx}"
                        issued_str = p.issued_at.isoformat() if p.issued_at else None
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO forecast_points (
                                point_id, snapshot_id, source_id, forecast_type,
                                fetched_at, issued_at, valid_at, lead_time_seconds,
                                temperature_c, apparent_temperature_c, dew_point_c,
                                humidity_pct, pressure_hpa, precipitation_probability_pct,
                                precipitation_mm, snow_mm, wind_speed_ms, wind_gust_ms,
                                wind_bearing_deg, cloud_cover_pct, uv_index, condition, raw_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                point_id,
                                snapshot.snapshot_id,
                                p.source_id,
                                p.forecast_type.value,
                                p.fetched_at.isoformat(),
                                issued_str,
                                p.valid_at.isoformat(),
                                p.lead_time.total_seconds(),
                                p.temperature_c,
                                p.apparent_temperature_c,
                                p.dew_point_c,
                                p.humidity_pct,
                                p.pressure_hpa,
                                p.precipitation_probability_pct,
                                p.precipitation_mm,
                                p.snow_mm,
                                p.wind_speed_ms,
                                p.wind_gust_ms,
                                p.wind_bearing_deg,
                                p.cloud_cover_pct,
                                p.uv_index,
                                p.condition,
                                p.raw_hash,
                            ),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_do_save)

    async def query_snapshots(
        self,
        source_id: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ForecastSnapshot]:
        """Query forecast snapshots from SQLite."""

        def _do_query() -> list[ForecastSnapshot]:
            conn = self._get_connection()
            try:
                query = "SELECT * FROM snapshots WHERE 1=1"
                params: list[Any] = []
                if source_id:
                    query += " AND source_id = ?"
                    params.append(source_id)
                if start_at:
                    query += " AND fetched_at >= ?"
                    params.append(start_at.isoformat())
                if end_at:
                    query += " AND fetched_at <= ?"
                    params.append(end_at.isoformat())
                query += " ORDER BY fetched_at DESC"

                snapshot_rows = conn.execute(query, params).fetchall()
                results: list[ForecastSnapshot] = []

                for srow in snapshot_rows:
                    pt_rows = conn.execute(
                        "SELECT * FROM forecast_points WHERE snapshot_id = ? ORDER BY valid_at ASC",
                        (srow["snapshot_id"],),
                    ).fetchall()
                    points: list[ForecastPoint] = []
                    for pr in pt_rows:
                        points.append(
                            ForecastPoint(
                                source_id=pr["source_id"],
                                forecast_type=ForecastType(pr["forecast_type"]),
                                fetched_at=ensure_utc(pr["fetched_at"]),  # type: ignore[arg-type]
                                issued_at=ensure_utc(pr["issued_at"]),
                                valid_at=ensure_utc(pr["valid_at"]),  # type: ignore[arg-type]
                                lead_time=datetime.fromtimestamp(0) - datetime.fromtimestamp(0),
                                temperature_c=pr["temperature_c"],
                                apparent_temperature_c=pr["apparent_temperature_c"],
                                dew_point_c=pr["dew_point_c"],
                                humidity_pct=pr["humidity_pct"],
                                pressure_hpa=pr["pressure_hpa"],
                                precipitation_probability_pct=pr["precipitation_probability_pct"],
                                precipitation_mm=pr["precipitation_mm"],
                                snow_mm=pr["snow_mm"],
                                wind_speed_ms=pr["wind_speed_ms"],
                                wind_gust_ms=pr["wind_gust_ms"],
                                wind_bearing_deg=pr["wind_bearing_deg"],
                                cloud_cover_pct=pr["cloud_cover_pct"],
                                uv_index=pr["uv_index"],
                                condition=pr["condition"],
                                raw_hash=pr["raw_hash"],
                            )
                        )
                    results.append(
                        ForecastSnapshot(
                            snapshot_id=srow["snapshot_id"],
                            source_id=srow["source_id"],
                            fetched_at=ensure_utc(srow["fetched_at"]),  # type: ignore[arg-type]
                            forecast_type=ForecastType(srow["forecast_type"]),
                            points=tuple(points),
                            raw_hash=srow["raw_hash"],
                        )
                    )
                return results
            finally:
                conn.close()

        return await asyncio.to_thread(_do_query)

    async def delete_forecasts_before(self, before: datetime) -> int:
        """Delete raw forecasts fetched before timestamp."""

        def _do_delete() -> int:
            conn = self._get_connection()
            try:
                before_str = before.isoformat()
                with conn:
                    cursor = conn.execute(
                        "DELETE FROM snapshots WHERE fetched_at < ?", (before_str,)
                    )
                    return cursor.rowcount
            finally:
                conn.close()

        return await asyncio.to_thread(_do_delete)

    async def save_observation(self, observation: Observation) -> None:
        """Save a ground truth observation."""

        def _do_save() -> None:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO observations (
                            observation_id, parameter, start_at, end_at, value,
                            unit, source_mode, source_entity_id, quality, entered_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            observation.observation_id,
                            observation.parameter.value,
                            observation.start_at.isoformat(),
                            observation.end_at.isoformat(),
                            str(observation.value),
                            observation.unit,
                            observation.source_mode.value,
                            observation.source_entity_id,
                            observation.quality.value,
                            observation.entered_at.isoformat(),
                            json.dumps(dict(observation.metadata)),
                        ),
                    )
            finally:
                conn.close()

        await asyncio.to_thread(_do_save)

    async def query_observations(
        self,
        parameter: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[Observation]:
        """Query observations."""

        def _do_query() -> list[Observation]:
            conn = self._get_connection()
            try:
                query = "SELECT * FROM observations WHERE 1=1"
                params: list[Any] = []
                if parameter:
                    query += " AND parameter = ?"
                    params.append(parameter)
                if start_at:
                    query += " AND start_at >= ?"
                    params.append(start_at.isoformat())
                if end_at:
                    query += " AND end_at <= ?"
                    params.append(end_at.isoformat())
                query += " ORDER BY start_at ASC"

                rows = conn.execute(query, params).fetchall()
                results: list[Observation] = []
                for r in rows:
                    raw_val = r["value"]
                    val: float | str | bool = raw_val
                    if raw_val.lower() == "true":
                        val = True
                    elif raw_val.lower() == "false":
                        val = False
                    else:
                        try:
                            val = float(raw_val)
                        except ValueError:
                            val = raw_val

                    metadata = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                    results.append(
                        Observation(
                            observation_id=r["observation_id"],
                            parameter=WeatherParameter(r["parameter"]),
                            start_at=ensure_utc(r["start_at"]),  # type: ignore[arg-type]
                            end_at=ensure_utc(r["end_at"]),  # type: ignore[arg-type]
                            value=val,
                            unit=r["unit"],
                            source_mode=ObservationSourceMode(r["source_mode"]),
                            source_entity_id=r["source_entity_id"],
                            quality=ObservationQuality(r["quality"]),
                            entered_at=ensure_utc(r["entered_at"]),  # type: ignore[arg-type]
                            metadata=metadata,
                        )
                    )
                return results
            finally:
                conn.close()

        return await asyncio.to_thread(_do_query)

    async def delete_observations_before(self, before: datetime) -> int:
        """Delete observations before timestamp."""

        def _do_delete() -> int:
            conn = self._get_connection()
            try:
                before_str = before.isoformat()
                with conn:
                    cursor = conn.execute(
                        "DELETE FROM observations WHERE end_at < ?", (before_str,)
                    )
                    return cursor.rowcount
            finally:
                conn.close()

        return await asyncio.to_thread(_do_delete)

    async def save_verification_results(self, results: list[VerificationResult]) -> None:
        """Save verification results."""

        def _do_save() -> None:
            conn = self._get_connection()
            try:
                with conn:
                    for vr in results:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO verification_results (
                                verification_id, source_id, parameter, lead_time_bucket,
                                valid_at, forecast_value, observed_value, error, abs_error,
                                brier_score, stability_delta, correction_benefit, verified_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                vr.verification_id,
                                vr.source_id,
                                vr.parameter.value,
                                vr.lead_time_bucket,
                                vr.valid_at.isoformat(),
                                str(vr.forecast_value),
                                str(vr.observed_value),
                                vr.error,
                                vr.abs_error,
                                vr.brier_score,
                                vr.stability_delta,
                                vr.correction_benefit,
                                vr.verified_at.isoformat(),
                            ),
                        )
            finally:
                conn.close()

        await asyncio.to_thread(_do_save)
