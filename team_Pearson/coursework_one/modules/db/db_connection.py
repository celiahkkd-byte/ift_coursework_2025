import os
from typing import Any, Optional


def get_db_connection() -> Optional[Any]:
    """
    Build a PostgreSQL connection from environment variables.
    Returns None when no compatible postgres client package is installed.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5439"))
    dbname = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    # Prefer psycopg v3, fallback to psycopg2 if available.
    try:
        import psycopg  # type: ignore

        return psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
    except ModuleNotFoundError:
        pass

    try:
        import psycopg2  # type: ignore

        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
    except ModuleNotFoundError:
        return None
