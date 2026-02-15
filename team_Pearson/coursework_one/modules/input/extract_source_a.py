from typing import Any, Dict, List


def extract_source_a(
    company_ids: List[str], run_date: str, backfill_years: int, frequency: str
) -> List[Dict[str, Any]]:
    """
    Placeholder extractor for source A.
    Role 6 should replace this with a real upstream data extraction.
    """
    _ = backfill_years
    return [
        {
            "company_id": cid,
            "observation_date": run_date,
            "factor_name": "source_a_metric",
            "factor_value": 1.0,
            "source": "source_a",
            "frequency": frequency,
        }
        for cid in company_ids
    ]
