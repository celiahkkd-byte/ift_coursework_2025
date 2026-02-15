from typing import Any, Dict, List


def extract_source_a(
    symbols: List[str], run_date: str, backfill_years: int, frequency: str
) -> List[Dict[str, Any]]:
    """
    Placeholder extractor for source A.
    Role 6 should replace this with a real upstream data extraction.
    """
    _ = backfill_years
    return [
        {
            "symbol": symbol,
            "as_of_date": run_date,
            "factor_name": "source_a_metric",
            "factor_value": 1.0,
            "source": "source_a",
            "metric_frequency": frequency,
        }
        for symbol in symbols
    ]
