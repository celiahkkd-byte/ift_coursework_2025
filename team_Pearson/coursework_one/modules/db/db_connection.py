from __future__ import annotations

import os
import psycopg2
from psycopg2.extensions import connection


def get_db_connection() -> connection:
    """
    Create a PostgreSQL connection using environment variables.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5439"))
    dbname = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    try:
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
    except psycopg2.OperationalError as e:
        raise RuntimeError(
            "PostgreSQL connection failed. Check Docker/Postgres is running and "
            "POSTGRES_HOST/PORT/DB/USER/PASSWORD environment variables are correct."
        ) from e
