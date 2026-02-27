from __future__ import annotations

"""Company universe access layer for PostgreSQL."""

import os
from typing import List, Optional

from sqlalchemy import text

from .db_connection import get_db_engine


def _test_mode_symbols(limit: int) -> list[str]:
    symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]
    return symbols[:limit]


def _normalize_country_allowlist(country_allowlist: Optional[List[str]]) -> List[str]:
    if not country_allowlist:
        return []
    out = []
    for country in country_allowlist:
        c = str(country).strip().upper()
        if c and c not in out:
            out.append(c)
    return out


def get_company_universe(
    company_limit: int, country_allowlist: Optional[List[str]] = None
) -> list[str]:
    """Return company symbols from ``systematic_equity.company_static``.

    Parameters
    ----------
    company_limit:
        Maximum number of symbols to return. Values below 1 are coerced to 1.
    country_allowlist:
        Optional list of country codes (e.g., ``["US", "GB"]``). If provided,
        only symbols from those countries are returned.

    Returns
    -------
    list[str]
        Ordered list of symbols. In test mode (``CW1_TEST_MODE=1``), returns a
        deterministic stub list.
    """
    limit = max(1, int(company_limit))
    countries = _normalize_country_allowlist(country_allowlist)

    if os.getenv("CW1_TEST_MODE") == "1":
        return _test_mode_symbols(limit)

    engine = get_db_engine()
    with engine.connect() as conn:
        errors = []
        for table_name in ("company_static", "equity_static"):
            params = {"limit": limit}
            where_clause = ""
            if countries:
                placeholders = []
                for i, country in enumerate(countries):
                    key = f"country_{i}"
                    placeholders.append(f":{key}")
                    params[key] = country
                where_clause = f"WHERE country IN ({', '.join(placeholders)})"

            sql = text(
                f"""
                SELECT symbol
                FROM systematic_equity.{table_name}
                {where_clause}
                ORDER BY symbol
                LIMIT :limit;
                """
            )
            try:
                rows = conn.execute(sql, params).fetchall()
                return [str(r[0]) for r in rows]
            except Exception as exc:
                errors.append(f"{table_name}: {exc}")

    raise RuntimeError(
        "Unable to read universe table from PostgreSQL. Tried "
        "systematic_equity.company_static and systematic_equity.equity_static. "
        "Run seed script: `poetry run python scripts/seed_universe_from_sqlite.py`. "
        f"Details: {errors}"
    )


def get_company_count() -> int:
    """
    Return total number of companies in systematic_equity.company_static.
    """
    if os.getenv("CW1_TEST_MODE") == "1":
        return len(_test_mode_symbols(10_000))

    engine = get_db_engine()
    with engine.connect() as conn:
        errors = []
        for table_name in ("company_static", "equity_static"):
            sql = text(f"SELECT COUNT(*) FROM systematic_equity.{table_name};")
            try:
                return int(conn.execute(sql).scalar_one())
            except Exception as exc:
                errors.append(f"{table_name}: {exc}")

    raise RuntimeError(
        "Unable to count universe rows from PostgreSQL. Tried "
        "systematic_equity.company_static and systematic_equity.equity_static. "
        "Run seed script: `poetry run python scripts/seed_universe_from_sqlite.py`. "
        f"Details: {errors}"
    )


if __name__ == "__main__":
    total = get_company_count()
    top10 = get_company_universe(10)

    print(f"Company count: {total}")
    print("Top 10 company symbols:")
    for symbol in top10:
        print(symbol)
