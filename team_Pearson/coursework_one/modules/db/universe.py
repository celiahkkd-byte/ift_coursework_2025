from __future__ import annotations

"""Company universe access layer for PostgreSQL."""

import os
from typing import List, Optional

from sqlalchemy import text

from .db_connection import get_db_engine

UNIVERSE_SELECT_SQL = {
    "company_static": """
    SELECT DISTINCT symbol
    FROM systematic_equity.company_static
    {where_clause}
    ORDER BY symbol
    {limit_clause}
    """,
    "equity_static": """
    SELECT DISTINCT symbol
    FROM systematic_equity.equity_static
    {where_clause}
    ORDER BY symbol
    {limit_clause}
    """,
}

UNIVERSE_COUNT_SQL = {
    "company_static": text("SELECT COUNT(*) FROM systematic_equity.company_static;"),
    "equity_static": text("SELECT COUNT(*) FROM systematic_equity.equity_static;"),
}


def _test_mode_symbols(limit: Optional[int]) -> list[str]:
    symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]
    if limit is None:
        return symbols
    return symbols[:limit]


def _normalize_country_allowlist(country_allowlist: Optional[object]) -> List[str]:
    if not country_allowlist:
        return []
    if isinstance(country_allowlist, str):
        items = [x for x in country_allowlist.split(",")]
    elif isinstance(country_allowlist, list):
        items = country_allowlist
    else:
        raise ValueError(
            "Invalid country_allowlist="
            f"{country_allowlist!r}. Expected list or comma-separated string."
        )
    out = []
    for country in items:
        c = str(country).strip().upper()
        if c and c not in out:
            out.append(c)
    return out


def _dedupe_symbols(symbols: List[str]) -> List[str]:
    """Deduplicate symbols while preserving original order."""
    seen = set()
    out: List[str] = []
    for raw in symbols:
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def get_company_universe(
    company_limit: Optional[int], country_allowlist: Optional[object] = None
) -> list[str]:
    """Return company symbols from ``systematic_equity.company_static``.

    Parameters
    ----------
    company_limit:
        Maximum number of symbols to return. ``None`` or values ``<=0`` mean unlimited.
    country_allowlist:
        Optional list of country codes (e.g., ``["US", "GB"]``). If provided,
        only symbols from those countries are returned.

    Returns
    -------
    list[str]
        Ordered list of symbols. In test mode (``CW1_TEST_MODE=1``), returns a
        deterministic stub list.
    """
    limit: Optional[int]
    if company_limit is None:
        limit = None
    else:
        parsed_limit = int(company_limit)
        limit = None if parsed_limit <= 0 else parsed_limit
    countries = _normalize_country_allowlist(country_allowlist)

    if os.getenv("CW1_TEST_MODE") == "1":
        return _test_mode_symbols(limit)

    engine = get_db_engine()
    with engine.connect() as conn:
        errors = []
        for table_name in ("company_static", "equity_static"):
            params = {}
            limit_clause = ""
            if limit is not None:
                params["limit"] = limit
                limit_clause = "LIMIT :limit"
            where_clause = ""
            if countries:
                placeholders = []
                for i, country in enumerate(countries):
                    key = f"country_{i}"
                    placeholders.append(f":{key}")
                    params[key] = country
                where_clause = f"WHERE country IN ({', '.join(placeholders)})"

            sql = text(
                UNIVERSE_SELECT_SQL[table_name].format(
                    where_clause=where_clause, limit_clause=limit_clause
                )
            )
            try:
                rows = conn.execute(sql, params).fetchall()
                return _dedupe_symbols([str(r[0]) for r in rows])
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
            sql = UNIVERSE_COUNT_SQL[table_name]
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
