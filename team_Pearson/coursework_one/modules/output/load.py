from __future__ import annotations

"""Database load helpers for curated factor observations."""

import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List

from modules.db import get_db_engine

logger = logging.getLogger(__name__)


def load_curated(
    records: List[Dict[str, Any]],
    *,
    dry_run: bool = False,
    table_name: str = "factor_observations",
) -> int:
    """Load curated records into PostgreSQL with upsert semantics.

    Parameters
    ----------
    records:
        Normalized records to insert/update.
    dry_run:
        If ``True``, skips DB I/O and returns the number of input records.
    table_name:
        Target table name in the configured schema.

    Returns
    -------
    int
        Number of records written (or would be written for ``dry_run``).

    Raises
    ------
    ModuleNotFoundError
        If pandas/SQLAlchemy are not installed.
    ValueError
        If required columns are missing in input records.
    """
    if not records:
        return 0
    if dry_run:
        return len(records)

    try:
        import pandas as pd  # type: ignore
        from sqlalchemy import MetaData, Table  # type: ignore
        from sqlalchemy.dialects.postgresql import insert as pg_insert  # type: ignore
    except ModuleNotFoundError as e:  # pragma: no cover
        raise ModuleNotFoundError(
            "Loading to Postgres requires pandas + SQLAlchemy. "
            "Install dependencies via Poetry: `poetry install`."
        ) from e

    df = pd.DataFrame.from_records(records)

    required = {"symbol", "observation_date", "factor_name"}
    if not required.issubset(df.columns):
        missing = required.difference(df.columns)
        raise ValueError(f"Missing required columns for load: {sorted(missing)}")

    schema = os.getenv("POSTGRES_SCHEMA", "systematic_equity")

    engine = get_db_engine()
    metadata = MetaData()
    table = Table(table_name, metadata, schema=schema, autoload_with=engine)

    table_columns = {c.name for c in table.columns}
    ignored_columns = sorted(c for c in df.columns if c not in table_columns)
    if ignored_columns:
        logger.debug("Ignored columns not in DB schema: %s", ", ".join(ignored_columns))

    writable_columns = [c for c in df.columns if c in table_columns]
    df = df[writable_columns]
    df = df.where(df.notna(), None)

    # Final defensive guard for date columns before SQL bind.
    if "observation_date" in df.columns:
        obs = pd.to_datetime(df["observation_date"], errors="coerce")
        df = df[obs.notna()].copy()
        if df.empty:
            return 0
        df["observation_date"] = obs[obs.notna()].dt.date.values

    if "source_report_date" in df.columns:
        report = pd.to_datetime(df["source_report_date"], errors="coerce")
        # Keep Python ``date`` or ``None`` only; avoid pandas NaT leaking into SQL binds.
        df["source_report_date"] = [ts.date() if pd.notna(ts) else None for ts in report]
    if "factor_value" in df.columns:
        df["factor_value"] = pd.to_numeric(df["factor_value"], errors="coerce")
        df["factor_value"] = df["factor_value"].map(
            lambda x: (
                None if (x is None or (isinstance(x, float) and not math.isfinite(x))) else float(x)
            )
        )

    records_out = df.to_dict(orient="records")
    stmt = pg_insert(table).values(records_out)

    update_dict = {
        "factor_value": stmt.excluded.factor_value,
        "source": stmt.excluded.source,
        "metric_frequency": stmt.excluded.metric_frequency,
        "source_report_date": stmt.excluded.source_report_date,
        "updated_at": datetime.now(),
    }

    upsert_stmt = stmt.on_conflict_do_update(
        constraint="uniq_observation",
        set_=update_dict,
    )

    with engine.begin() as conn:
        conn.execute(upsert_stmt)

    return len(records_out)


def load_financial_observations(
    records: List[Dict[str, Any]],
    *,
    dry_run: bool = False,
    table_name: str = "financial_observations",
) -> int:
    """Load atomic financial observations into PostgreSQL with upsert semantics."""
    if not records:
        return 0
    if dry_run:
        return len(records)

    try:
        import pandas as pd  # type: ignore
        from sqlalchemy import MetaData, Table  # type: ignore
        from sqlalchemy.dialects.postgresql import insert as pg_insert  # type: ignore
    except ModuleNotFoundError as e:  # pragma: no cover
        raise ModuleNotFoundError(
            "Loading to Postgres requires pandas + SQLAlchemy. "
            "Install dependencies via Poetry: `poetry install`."
        ) from e

    df = pd.DataFrame.from_records(records)
    required = {"symbol", "report_date", "metric_name"}
    if not required.issubset(df.columns):
        missing = required.difference(df.columns)
        raise ValueError(f"Missing required columns for financial load: {sorted(missing)}")

    schema = os.getenv("POSTGRES_SCHEMA", "systematic_equity")
    engine = get_db_engine()
    metadata = MetaData()
    table = Table(table_name, metadata, schema=schema, autoload_with=engine)

    table_columns = {c.name for c in table.columns}
    writable_columns = [c for c in df.columns if c in table_columns]
    df = df[writable_columns]
    df = df.where(df.notna(), None)

    report = pd.to_datetime(df["report_date"], errors="coerce")
    df = df[report.notna()].copy()
    if df.empty:
        return 0
    df["report_date"] = report[report.notna()].dt.date.values

    if "as_of" in df.columns:
        as_of = pd.to_datetime(df["as_of"], errors="coerce")
        df["as_of"] = [ts.date() if pd.notna(ts) else None for ts in as_of]

    if "metric_value" in df.columns:
        df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
        df["metric_value"] = df["metric_value"].map(
            lambda x: (
                None if (x is None or (isinstance(x, float) and not math.isfinite(x))) else float(x)
            )
        )

    records_out = df.to_dict(orient="records")
    stmt = pg_insert(table).values(records_out)
    update_dict = {
        "metric_value": stmt.excluded.metric_value,
        "currency": stmt.excluded.currency,
        "period_type": stmt.excluded.period_type,
        "source": stmt.excluded.source,
        "as_of": stmt.excluded.as_of,
        "metric_definition": stmt.excluded.metric_definition,
        "updated_at": datetime.now(),
    }
    upsert_stmt = stmt.on_conflict_do_update(
        constraint="uniq_financial_observation",
        set_=update_dict,
    )
    with engine.begin() as conn:
        conn.execute(upsert_stmt)
    return len(records_out)
