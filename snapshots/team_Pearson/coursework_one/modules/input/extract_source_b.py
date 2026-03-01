from __future__ import annotations

"""Unstructured extractor (Source B) interface stubs.

This module keeps a stable two-stage contract:
1) ingest raw unstructured payloads
2) transform payloads to curated factor records
"""

import os
from typing import Any, Dict, List, Optional


def ingest_source_b_raw(
    symbols: List[str],
    run_date: str,
    backfill_years: int,
    frequency: str,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Ingest raw Source B payloads.

    Parameters
    ----------
    symbols:
        Target symbols.
    run_date:
        Pipeline run date in ``YYYY-MM-DD`` format.
    backfill_years:
        Historical lookback window in years.
    frequency:
        Scheduling frequency label.
    config:
        Optional runtime configuration.

    Returns
    -------
    list[dict[str, Any]]
        Raw payload list for feature transformation. Current implementation is
        a stub and returns an empty list.
    """
    _ = (symbols, run_date, backfill_years, frequency, config)
    return []


def transform_source_b_features(
    raw_payloads: List[Dict[str, Any]],
    symbols: List[str],
    run_date: str,
    frequency: str,
) -> List[Dict[str, Any]]:
    """Transform raw Source B payloads to curated records.

    Parameters
    ----------
    raw_payloads:
        Raw records returned by :func:`ingest_source_b_raw`.
    symbols:
        Target symbols for transformation.
    run_date:
        Pipeline run date in ``YYYY-MM-DD`` format.
    frequency:
        Scheduling frequency label.

    Returns
    -------
    list[dict[str, Any]]
        Curated records matching the common extractor output contract.
    """
    _ = raw_payloads
    if os.getenv("CW1_TEST_MODE") == "1":
        return [
            {
                "symbol": symbol,
                "observation_date": run_date,
                "factor_name": "source_b_metric",
                "value": 2.0,
                "source": "extractor_b",
                "frequency": frequency,
            }
            for symbol in symbols
        ]
    return []


def extract_source_b(
    symbols: List[str],
    run_date: str,
    backfill_years: int,
    frequency: str,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run Source B end-to-end (ingest + transform).

    Parameters
    ----------
    symbols:
        Target symbols.
    run_date:
        Pipeline run date in ``YYYY-MM-DD`` format.
    backfill_years:
        Historical lookback window in years.
    frequency:
        Scheduling frequency label.
    config:
        Optional runtime configuration.

    Returns
    -------
    list[dict[str, Any]]
        Curated records from Source B.
    """
    raw_payloads = ingest_source_b_raw(symbols, run_date, backfill_years, frequency, config=config)
    return transform_source_b_features(raw_payloads, symbols, run_date, frequency)
