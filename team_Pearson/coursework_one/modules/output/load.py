from typing import Any, Dict, List

from modules.db import get_db_connection


def load_curated(records: List[Dict[str, Any]], dry_run: bool) -> int:
    """
    Load normalized records into PostgreSQL with idempotent upsert semantics.
    """
    if dry_run:
        return 0

    if not records:
        return 0

    conn = get_db_connection()
    if conn is None:
        raise RuntimeError(
            "PostgreSQL connector not available. Install psycopg/psycopg2 to enable DB loading."
        )

    upsert_sql = """
        INSERT INTO systematic_equity.factor_observations (
            symbol, as_of_date, factor_name, factor_value, source,
            metric_frequency, source_report_date, run_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, factor_name, as_of_date)
        DO UPDATE SET
            factor_value = EXCLUDED.factor_value,
            source = EXCLUDED.source,
            metric_frequency = EXCLUDED.metric_frequency,
            source_report_date = EXCLUDED.source_report_date,
            run_id = EXCLUDED.run_id,
            updated_at = NOW()
    """

    loaded = 0
    try:
        with conn.cursor() as cur:
            for rec in records:
                cur.execute(
                    upsert_sql,
                    (
                        rec.get("symbol"),
                        rec.get("as_of_date"),
                        rec.get("factor_name"),
                        rec.get("factor_value"),
                        rec.get("source", "unknown"),
                        rec.get("metric_frequency", "unknown"),
                        rec.get("source_report_date"),
                        rec.get("run_id"),
                    ),
                )
                loaded += 1
        conn.commit()
        return loaded
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
