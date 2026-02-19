from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _to_iso_date(x: Any) -> Optional[str]:
    """
    Convert common date-like inputs to 'YYYY-MM-DD' string.
    Returns None if input is None/empty.
    """
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date().isoformat()
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        # Best-effort: accept 'YYYY-MM-DD...' (with time)
        return s[:10]
    # Unknown type -> keep None so quality can flag missing/invalid
    return None


def _to_float_or_none(x: Any) -> Optional[float]:
    """
    Convert to float when possible.
    Treat '', 'nan', 'None' as None. Return None on unparseable values.
    """
    if x is None:
        return None
    if isinstance(x, (int, float)):
        # handle NaN
        try:
            if x != x:  # NaN check
                return None
        except Exception:
            pass
        return float(x)

    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        if s.lower() in {"nan", "none", "null"}:
            return None
        # remove common thousands separators
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    # Unhandled type
    return None


def normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize raw records into a shared long-format schema.

    Output schema (kept stable for downstream load):
      - symbol
      - observation_date (YYYY-MM-DD string)
      - factor_name
      - factor_value (float or None)
      - source
      - metric_frequency
      - source_report_date (YYYY-MM-DD string or None)
      - run_id (optional passthrough)

    Input tolerance:
      - symbol may come from 'symbol' or 'company_id'
      - observation_date may come from 'observation_date' or 'date' or 'as_of'
      - factor_name may come from 'factor_name' or 'metric'
      - factor_value may come from 'factor_value' or 'value'
      - metric_frequency may come from 'metric_frequency' or 'frequency'
    """
    normalized: List[Dict[str, Any]] = []

    for rec in records:
        symbol = rec.get("symbol") or rec.get("company_id")

        obs_date_raw = rec.get("observation_date") or rec.get("date") or rec.get("as_of")
        observation_date = _to_iso_date(obs_date_raw)

        factor_name = rec.get("factor_name") or rec.get("metric") or "unknown_factor"

        # Prefer explicit factor_value if present, otherwise fall back to value
        raw_value = rec.get("factor_value") if "factor_value" in rec else rec.get("value")
        factor_value = _to_float_or_none(raw_value)

        source = rec.get("source", "unknown")

        freq = rec.get("metric_frequency") or rec.get("frequency") or "unknown"
        metric_frequency = str(freq).strip().lower() if freq is not None else "unknown"

        source_report_date = _to_iso_date(rec.get("source_report_date"))

        normalized.append(
            {
                "symbol": symbol,
                "observation_date": observation_date,
                "factor_name": factor_name,
                "factor_value": factor_value,
                "source": source,
                "metric_frequency": metric_frequency,
                "source_report_date": source_report_date,
                "run_id": rec.get("run_id"),
            }
        )

    return normalized
