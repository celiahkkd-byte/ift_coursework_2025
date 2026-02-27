from __future__ import annotations

"""PostgreSQL connection utilities based on environment variables."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5439")
    dbname = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def get_db_engine() -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL.

    Returns
    -------
    sqlalchemy.engine.Engine
        Database engine configured from ``POSTGRES_*`` environment variables.

    Raises
    ------
    RuntimeError
        If engine initialization fails.
    """
    try:
        return create_engine(_build_db_url())
    except Exception as e:
        raise RuntimeError(
            "PostgreSQL engine initialization failed. Check Docker/Postgres is running and "
            "POSTGRES_HOST/PORT/DB/USER/PASSWORD environment variables are correct."
        ) from e


def get_db_connection():
    """Backward-compatible raw DB-API connection for existing callers."""
    engine = get_db_engine()
    return engine.raw_connection()
