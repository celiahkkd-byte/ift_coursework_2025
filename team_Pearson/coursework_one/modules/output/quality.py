from typing import Any, Dict, List, Tuple


def run_quality_checks(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Basic quality checks for normalized records.
    Role 8 can expand this with outlier/threshold checks.
    """
    missing_values = sum(1 for r in records if r.get("factor_value") is None)

    seen: set[Tuple[Any, Any, Any, Any]] = set()
    duplicates = 0
    for r in records:
        key = (
            r.get("symbol"),
            r.get("observation_date"),
            r.get("factor_name"),
            r.get("source"),
        )
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)

    return {
        "row_count": len(records),
        "missing_values": missing_values,
        "duplicates": duplicates,
    }
