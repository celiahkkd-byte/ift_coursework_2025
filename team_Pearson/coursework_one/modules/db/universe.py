from typing import List

from .db_connection import get_db_connection


def _fallback_symbols(limit: int) -> List[str]:
    return [f"SYM{i:05d}" for i in range(1, limit + 1)]


def get_company_universe(company_limit: int) -> List[str]:
    """
    Read symbols dynamically from systematic_equity.company_static.
    Falls back to local mock symbols when DB connector is unavailable.
    """
    limit = max(1, int(company_limit))
    try:
        conn = get_db_connection()
    except Exception:
        return _fallback_symbols(limit)

    if conn is None:
        return _fallback_symbols(limit)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol
                FROM systematic_equity.company_static
                WHERE symbol IS NOT NULL
                  AND TRIM(symbol) <> ''
                ORDER BY symbol
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            symbols = [r[0] for r in rows if r and r[0]]
            return symbols or _fallback_symbols(limit)
    except Exception:
        return _fallback_symbols(limit)
    finally:
        conn.close()
