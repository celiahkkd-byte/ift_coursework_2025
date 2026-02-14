from typing import List


def get_company_universe(company_limit: int) -> List[str]:
    """
    Placeholder universe provider.
    Role 5 can replace this with DB-backed retrieval from company_static.
    """
    limit = max(1, int(company_limit))
    return [f"C{i:05d}" for i in range(1, limit + 1)]
