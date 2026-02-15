from typing import Any, Dict, List


def normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize raw records into a shared long-format schema.
    Role 8 can extend mappings and validation rules.
    """
    normalized: List[Dict[str, Any]] = []
    for rec in records:
        normalized.append(
            {
                "company_id": rec.get("company_id"),
                "observation_date": rec.get("observation_date") or rec.get("date") or rec.get("as_of"),
                "factor_name": rec.get("factor_name") or rec.get("metric") or "unknown_factor",
                "factor_value": rec.get("factor_value") if "factor_value" in rec else rec.get("value"),
                "source": rec.get("source", "unknown"),
            }
        )
    return normalized
