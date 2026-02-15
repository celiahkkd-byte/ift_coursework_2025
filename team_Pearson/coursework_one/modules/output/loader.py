"""Compatibility wrapper for teams using loader.py naming."""

from typing import Any, Dict, List

from .load import load_curated


def load_records(records: List[Dict[str, Any]], dry_run: bool = True) -> int:
    """Alias API that delegates to the canonical load_curated implementation."""
    return load_curated(records, dry_run=dry_run)
