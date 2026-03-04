"""Database helpers for Airviro ETL loading."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    import psycopg2
    from psycopg2 import extras
    from psycopg2.extensions import connection as PgConnection
except ImportError as exc:  # pragma: no cover - runtime environment concern
    raise RuntimeError(
        "psycopg2 is required. Run inside the project virtualenv: .venv/bin/python ..."
    ) from exc

from .config import Settings
from .pipeline import MeasurementRow


def connect_warehouse(settings: Settings) -> tuple[PgConnection, str]:
    """Connect to warehouse DB using candidate hosts.

    Returns:
      (connection, selected_host)
    """

    last_error: Exception | None = None
    for host in settings.candidate_db_hosts():
        try:
            conn = psycopg2.connect(
                host=host,
                port=settings.warehouse_db_port,
                dbname=settings.warehouse_db_name,
                user=settings.warehouse_db_user,
                password=settings.warehouse_db_password,
                connect_timeout=5,
            )
            conn.autocommit = False
            return conn, host
        except Exception as exc:  # pragma: no cover - connection failure path
            last_error = exc

    raise RuntimeError(
        f"Unable to connect to warehouse using hosts {settings.candidate_db_hosts()}: {last_error}"
    )


def apply_schema(connection: PgConnection, sql_path: Path) -> None:
    """Apply schema bootstrap SQL."""

    sql_text = sql_path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        cursor.execute(sql_text)
    connection.commit()


def collect_warehouse_status(
    connection: PgConnection,
    *,
    indicator_limit: int = 500,
    audit_limit: int = 10,
) -> dict[str, Any]:
    """Collect warehouse-health and data-completeness metrics.

    Args:
      connection: Open warehouse connection.
      indicator_limit: Maximum number of indicator-level rows to return.
      audit_limit: Maximum number of most-recent audit rows to return.
    """

    if indicator_limit < 1:
        raise ValueError("indicator_limit must be >= 1")
    if audit_limit < 1:
        raise ValueError("audit_limit must be >= 1")

    status: dict[str, Any] = {}
    with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT
              current_database() AS database_name,
              current_user AS database_user,
              now() AT TIME ZONE 'UTC' AS collected_at_utc
            """
        )
        status["database"] = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT
              to_regclass('raw.airviro_measurement') IS NOT NULL AS has_measurement_table,
              to_regclass('raw.airviro_ingestion_audit') IS NOT NULL AS has_ingestion_audit_table,
              to_regclass('raw.pipeline_watermark') IS NOT NULL AS has_pipeline_watermark_table
            """
        )
        table_status = dict(cursor.fetchone())
        status["table_status"] = table_status

        if not table_status["has_measurement_table"]:
            status["warning"] = (
                "raw.airviro_measurement does not exist yet. "
                "Run bootstrap first: make etl-bootstrap"
            )
            return status

        cursor.execute(
            """
            SELECT
              COUNT(*)::bigint AS measurement_rows,
              COUNT(DISTINCT source_type)::int AS source_type_count,
              COUNT(DISTINCT station_id)::int AS station_count,
              COUNT(DISTINCT indicator_code)::int AS indicator_count,
              MIN(observed_at) AS first_observed_at,
              MAX(observed_at) AS last_observed_at,
              COUNT(*) FILTER (WHERE value_numeric IS NULL)::bigint AS null_value_rows
            FROM raw.airviro_measurement
            """
        )
        status["measurement_totals"] = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT
              source_type,
              station_id,
              COUNT(*)::bigint AS row_count,
              COUNT(DISTINCT indicator_code)::int AS indicator_count,
              COUNT(*) FILTER (WHERE value_numeric IS NULL)::bigint AS null_value_rows,
              MIN(observed_at) AS first_observed_at,
              MAX(observed_at) AS last_observed_at
            FROM raw.airviro_measurement
            GROUP BY source_type, station_id
            ORDER BY source_type, station_id
            """
        )
        status["coverage_by_source"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            WITH indicator_span AS (
              SELECT
                source_type,
                station_id,
                indicator_code,
                MIN(observed_at) AS first_observed_at,
                MAX(observed_at) AS last_observed_at,
                COUNT(*)::bigint AS row_count,
                COUNT(*) FILTER (WHERE value_numeric IS NULL)::bigint AS null_value_rows
              FROM raw.airviro_measurement
              GROUP BY source_type, station_id, indicator_code
            ),
            indicator_completeness AS (
              SELECT
                source_type,
                station_id,
                indicator_code,
                row_count,
                null_value_rows,
                first_observed_at,
                last_observed_at,
                CASE
                  WHEN source_type = 'pollen' THEN 'daily'
                  ELSE 'hourly'
                END AS expected_grain,
                CASE
                  WHEN first_observed_at IS NULL OR last_observed_at IS NULL THEN 0::bigint
                  WHEN source_type = 'pollen' THEN ((EXTRACT(EPOCH FROM (last_observed_at - first_observed_at)) / 86400)::bigint + 1)
                  ELSE ((EXTRACT(EPOCH FROM (last_observed_at - first_observed_at)) / 3600)::bigint + 1)
                END AS expected_rows
              FROM indicator_span
            )
            SELECT
              source_type,
              station_id,
              indicator_code,
              row_count,
              expected_grain,
              expected_rows,
              GREATEST(expected_rows - row_count, 0)::bigint AS missing_rows,
              ROUND(
                (GREATEST(expected_rows - row_count, 0)::numeric / NULLIF(expected_rows, 0)::numeric) * 100,
                2
              ) AS missing_pct,
              null_value_rows,
              ROUND((null_value_rows::numeric / NULLIF(row_count, 0)::numeric) * 100, 2) AS null_value_pct,
              first_observed_at,
              last_observed_at
            FROM indicator_completeness
            ORDER BY source_type, station_id, indicator_code
            LIMIT %s
            """,
            (indicator_limit,),
        )
        status["indicator_completeness"] = [dict(row) for row in cursor.fetchall()]

        if table_status["has_pipeline_watermark_table"]:
            cursor.execute(
                """
                SELECT
                  pipeline_name,
                  watermark_date,
                  updated_at
                FROM raw.pipeline_watermark
                ORDER BY pipeline_name
                """
            )
            status["watermarks"] = [dict(row) for row in cursor.fetchall()]
        else:
            status["watermarks"] = []

        if table_status["has_ingestion_audit_table"]:
            cursor.execute(
                """
                SELECT
                  created_at,
                  batch_id,
                  source_key,
                  source_type,
                  station_id,
                  window_start,
                  window_end,
                  rows_read,
                  records_upserted,
                  duplicate_records,
                  split_events,
                  status
                FROM raw.airviro_ingestion_audit
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (audit_limit,),
            )
            status["recent_ingestion_runs"] = [dict(row) for row in cursor.fetchall()]
        else:
            status["recent_ingestion_runs"] = []

    return status


def upsert_measurements(connection: PgConnection, rows: Iterable[MeasurementRow]) -> int:
    """Insert or update normalized measurements."""

    payload = [
        (
            row.source_type,
            row.station_id,
            row.observed_at,
            row.indicator_code,
            row.indicator_name,
            row.value_numeric,
            row.source_row_hash,
        )
        for row in rows
    ]
    if not payload:
        return 0

    query = """
    INSERT INTO raw.airviro_measurement (
      source_type,
      station_id,
      observed_at,
      indicator_code,
      indicator_name,
      value_numeric,
      source_row_hash
    )
    VALUES %s
    ON CONFLICT (source_type, station_id, observed_at, indicator_code)
    DO UPDATE SET
      indicator_name = EXCLUDED.indicator_name,
      value_numeric = EXCLUDED.value_numeric,
      source_row_hash = EXCLUDED.source_row_hash,
      extracted_at = now();
    """

    with connection.cursor() as cursor:
        extras.execute_values(cursor, query, payload, page_size=5000)
    connection.commit()
    return len(payload)


def refresh_dimensions(connection: PgConnection) -> None:
    """Refresh dimension tables from loaded raw facts."""

    refresh_sql = """
    INSERT INTO mart.dim_indicator (source_type, indicator_code, indicator_name)
    SELECT DISTINCT source_type, indicator_code, indicator_name
    FROM raw.airviro_measurement
    ON CONFLICT DO NOTHING;

    UPDATE mart.dim_indicator AS target
    SET indicator_name = source.indicator_name
    FROM (
      SELECT DISTINCT source_type, indicator_code, indicator_name
      FROM raw.airviro_measurement
    ) AS source
    WHERE target.source_type = source.source_type
      AND target.indicator_code = source.indicator_code
      AND target.indicator_name IS DISTINCT FROM source.indicator_name;

    INSERT INTO mart.dim_datetime_hour (
      observed_at,
      date_value,
      year_number,
      quarter_number,
      month_number,
      month_name,
      day_number,
      hour_number,
      iso_week_number,
      day_of_week_number,
      day_name
    )
    SELECT
      source.observed_at,
      source.observed_at::date,
      EXTRACT(YEAR FROM source.observed_at)::int,
      EXTRACT(QUARTER FROM source.observed_at)::int,
      EXTRACT(MONTH FROM source.observed_at)::int,
      TO_CHAR(source.observed_at, 'Month'),
      EXTRACT(DAY FROM source.observed_at)::int,
      EXTRACT(HOUR FROM source.observed_at)::int,
      EXTRACT(WEEK FROM source.observed_at)::int,
      EXTRACT(ISODOW FROM source.observed_at)::int,
      TO_CHAR(source.observed_at, 'Dy')
    FROM (
      SELECT DISTINCT observed_at
      FROM raw.airviro_measurement
    ) AS source
    WHERE NOT EXISTS (
      SELECT 1
      FROM mart.dim_datetime_hour AS target
      WHERE target.observed_at = source.observed_at
    );
    """

    with connection.cursor() as cursor:
        cursor.execute(refresh_sql)
    connection.commit()


def log_ingestion_audit(
    connection: PgConnection,
    *,
    batch_id: str,
    source_key: str,
    source_type: str,
    station_id: int,
    window_start: datetime,
    window_end: datetime,
    rows_read: int,
    records_upserted: int,
    duplicate_records: int,
    split_events: int,
    status: str,
    message: str | None = None,
) -> None:
    """Insert one ingestion-audit record."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO raw.airviro_ingestion_audit (
              batch_id,
              source_key,
              source_type,
              station_id,
              window_start,
              window_end,
              rows_read,
              records_upserted,
              duplicate_records,
              split_events,
              status,
              message
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                batch_id,
                source_key,
                source_type,
                station_id,
                window_start,
                window_end,
                rows_read,
                records_upserted,
                duplicate_records,
                split_events,
                status,
                message,
            ),
        )
    connection.commit()
