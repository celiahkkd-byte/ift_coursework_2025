from typing import Any, Dict, List


def extract_source_b(
    company_ids: List[str], run_date: str, backfill_years: int, frequency: str
) -> List[Dict[str, Any]]:
    """
    Placeholder extractor for source B.
    Role 7 should replace this with a real upstream data extraction.
    """
    _ = backfill_years
    return [
        {
            "company_id": cid,
            "observation_date": run_date,
            "factor_name": "source_b_metric",
            "factor_value": 2.0,
            "source": "source_b",
            "frequency": frequency,
        }
        for cid in company_ids
    ]
