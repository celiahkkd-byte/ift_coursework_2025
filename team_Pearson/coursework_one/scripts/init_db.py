from __future__ import annotations

"""Initialize PostgreSQL schema/tables and seed company universe."""

import argparse
import os
import subprocess  # nosec B404
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize CW1 database by applying sql/init.sql and then seeding "
            "systematic_equity.company_static from teacher SQLite."
        )
    )
    parser.add_argument(
        "--container",
        default=os.getenv("POSTGRES_CONTAINER", "postgres_db_cw"),
        help="PostgreSQL container name (default: postgres_db_cw).",
    )
    parser.add_argument(
        "--db-user",
        default=os.getenv("POSTGRES_USER", "postgres"),
        help="PostgreSQL user for docker exec psql.",
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("POSTGRES_DB", "postgres"),
        help="PostgreSQL database for docker exec psql.",
    )
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Optional override for source SQLite Equity.db path.",
    )
    return parser.parse_args()


def run_sql_init(container: str, db_user: str, db_name: str, init_sql_path: Path) -> None:
    if not init_sql_path.exists():
        raise FileNotFoundError(f"init.sql not found: {init_sql_path}")

    sql_bytes = init_sql_path.read_bytes()
    cmd = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
    ]
    subprocess.run(cmd, input=sql_bytes, check=True)  # nosec B603


def run_seed(sqlite_path: str | None) -> None:
    cmd = [sys.executable, "scripts/seed_universe_from_sqlite.py"]
    if sqlite_path:
        cmd.extend(["--sqlite-path", sqlite_path])
    subprocess.run(cmd, check=True)  # nosec B603


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    init_sql_path = project_root / "sql" / "init.sql"

    run_sql_init(args.container, args.db_user, args.db_name, init_sql_path)
    run_seed(args.sqlite_path)
    print("DB init completed: schema/tables applied and universe seeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
