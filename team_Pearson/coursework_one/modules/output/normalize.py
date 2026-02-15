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
                "symbol": rec.get("symbol"),
                "observation_date": rec.get("observation_date") or rec.get("date") or rec.get("as_of"),
                "factor_name": rec.get("factor_name") or rec.get("metric") or "unknown_factor",
                "factor_value": rec.get("factor_value") if "factor_value" in rec else rec.get("value"),
                "source": rec.get("source", "unknown"),
                "metric_frequency": rec.get("metric_frequency") or rec.get("frequency") or "unknown",
                "source_report_date": rec.get("source_report_date"),
                "run_id": rec.get("run_id"),
            }
        )
    return normalized
