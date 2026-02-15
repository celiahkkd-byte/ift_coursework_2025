from __future__ import annotations

from .db_connection import get_db_connection


def get_company_universe(company_limit: int) -> list[str]:
    """
    Return company symbols from systematic_equity.company_static.
    """
    limit = max(1, int(company_limit))

    sql = """
        SELECT symbol
        FROM systematic_equity.company_static
        ORDER BY symbol
        LIMIT %s;
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            return [str(r[0]) for r in rows]
    finally:
        conn.close()


def get_company_count() -> int:
    """
    Return total number of companies in systematic_equity.company_static.
    """
    sql = "SELECT COUNT(*) FROM systematic_equity.company_static;"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return int(cur.fetchone()[0])
    finally:
        conn.close()


if __name__ == "__main__":
    total = get_company_count()
    top10 = get_company_universe(10)

    print(f"Company count: {total}")
    print("Top 10 company symbols:")
    for symbol in top10:
        print(symbol)






