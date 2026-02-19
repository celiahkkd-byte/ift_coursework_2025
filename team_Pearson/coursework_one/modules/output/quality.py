from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


_ALLOWED_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly", "annual", "unknown"}


def _is_missing_required(r: Dict[str, Any]) -> bool:
    return (
        not r.get("symbol")
        or not r.get("observation_date")
        or not r.get("factor_name")
        or not r.get("source")
        or not r.get("metric_frequency")
    )


def _is_invalid_frequency(freq: Optional[str]) -> bool:
    if freq is None:
        return True
    return str(freq).strip().lower() not in _ALLOWED_FREQUENCIES


def _is_non_finite_number(x: Any) -> bool:
    # factor_value should be float or None after normalize; still guard.
    if x is None:
        return False
    if not isinstance(x, (int, float)):
        return True
    try:
        # NaN or inf checks
        if x != x:
            return True
        if x == float("inf") or x == float("-inf"):
            return True
    except Exception:
        return True
    return False


def run_quality_checks(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Quality checks for normalized records.

    Keeps backward-compatible keys:
      - row_count
      - missing_values  (factor_value is None)
      - duplicates      (DB-unique-key duplicates)

    Adds extra helpful counters (won't break downstream):
      - missing_required
      - invalid_frequency
      - non_numeric_or_non_finite

    IMPORTANT: duplicates are counted using the DB unique key:
      (symbol, factor_name, observation_date)
    This matches init.sql + load.py ON CONFLICT behavior.
    """
    row_count = len(records)
    missing_values = sum(1 for r in records if r.get("factor_value") is None)
    missing_required = sum(1 for r in records if _is_missing_required(r))
    invalid_frequency = sum(1 for r in records if _is_invalid_frequency(r.get("metric_frequency")))
    non_numeric_or_non_finite = sum(1 for r in records if _is_non_finite_number(r.get("factor_value")))

    # Duplicates by DB unique key
    seen: set[Tuple[Any, Any, Any]] = set()
    duplicates = 0
    for r in records:
        key = (r.get("symbol"), r.get("factor_name"), r.get("observation_date"))
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)

    # Overall pass/fail (simple, explainable)
    passed = (missing_required == 0) and (invalid_frequency == 0)

    return {
        "row_count": row_count,
        "missing_values": missing_values,
        "duplicates": duplicates,
        "missing_required": missing_required,
        "invalid_frequency": invalid_frequency,
        "non_numeric_or_non_finite": non_numeric_or_non_finite,
        "passed": passed,
    }
