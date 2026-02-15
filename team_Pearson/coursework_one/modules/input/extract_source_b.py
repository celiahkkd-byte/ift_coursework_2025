from typing import Any, Dict, List


def extract_source_b(
    symbols: List[str], run_date: str, backfill_years: int, frequency: str
) -> List[Dict[str, Any]]:
    """
    Placeholder extractor for source B.
    Role 7 should replace this with a real upstream data extraction.
    """
    _ = backfill_years
    return [
        {
            "symbol": symbol,
            "as_of_date": run_date,
            "factor_name": "source_b_metric",
            "factor_value": 2.0,
            "source": "source_b",
            "metric_frequency": frequency,
        }
        for symbol in symbols
    ]
