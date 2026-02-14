from typing import Any, Dict, List


def load_curated(records: List[Dict[str, Any]], dry_run: bool) -> int:
    """
    Placeholder loader.
    Role 3 can replace this with PostgreSQL/MinIO persistence logic.
    """
    if dry_run:
        return 0
    return len(records)
