import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from modules.db import get_company_universe
from modules.input import extract_source_a, extract_source_b
from modules.output import load_curated, normalize_records, run_quality_checks

ALLOWED_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly", "annual"}


@dataclass
class RunLog:
    run_id: str
    start_time_utc: str
    end_time_utc: str
    run_date: str
    frequency: str
    backfill_years: int
    company_limit: int
    stages_ok: int
    stages_failed: int
    status: str
    error: str = ""
    notes: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    if yaml is None:
        # Allow pipeline to run in minimal local environments without pyyaml.
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_jsonl(path: str, record: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def collect_raw_records(
    company_ids: List[str], run_date: str, frequency: str, backfill_years: int
) -> List[Dict[str, Any]]:
    """Merge records from the currently integrated source modules."""
    raw_a = extract_source_a(company_ids, run_date, backfill_years, frequency)
    raw_b = extract_source_b(company_ids, run_date, backfill_years, frequency)
    return raw_a + raw_b


# -------------------------
# Scheduling stub (mock)
# -------------------------
def scheduling_stub(frequency: str) -> str:
    """
    Mock scheduling layer to satisfy 'Application Flexibility'.
    Later you can replace this with APScheduler/Airflow, but the interface stays.
    """
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return f"Scheduling stub configured for: {frequency}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CW1 pipeline skeleton (Team Pearson).")
    p.add_argument(
        "--config",
        default="config/conf.yaml",
        help="Path to YAML config relative to coursework_one/",
    )
    p.add_argument(
        "--run-date", required=True, help="Run date in YYYY-MM-DD (decision time, not shifted)."
    )
    p.add_argument("--frequency", required=True, choices=sorted(ALLOWED_FREQUENCIES))
    p.add_argument(
        "--backfill-years",
        type=int,
        default=None,
        help="How many years of history to fetch (default from config).",
    )
    p.add_argument(
        "--company-limit",
        type=int,
        default=None,
        help="Limit companies for debugging (default from config).",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Run pipeline without loading to storage (stub)."
    )
    return p.parse_args()


def resolve_paths(base_dir: str, config_path: str) -> str:
    # allow both relative and absolute config path
    if os.path.isabs(config_path):
        return config_path
    return os.path.join(base_dir, config_path)


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    args = parse_args()

    cfg_path = resolve_paths(base_dir, args.config)
    cfg = load_yaml(cfg_path)

    pipeline_cfg = cfg.get("pipeline") or {}
    log_cfg = cfg.get("logging") or {}

    backfill_years = (
        args.backfill_years
        if args.backfill_years is not None
        else int(pipeline_cfg.get("backfill_years", 5))
    )
    company_limit = (
        args.company_limit
        if args.company_limit is not None
        else int(pipeline_cfg.get("company_limit", 20))
    )

    run_id = str(uuid.uuid4())
    start = utc_now_iso()

    stages_ok = 0
    stages_failed = 0
    status = "success"
    err = ""
    notes = ""

    # schedule stub (mock)
    try:
        notes = scheduling_stub(args.frequency)
        stages_ok += 1
    except Exception as e:
        status = "failed"
        err = f"scheduling_stub_error: {repr(e)}"
        stages_failed += 1

    loaded_rows = 0
    quality_report: Optional[Dict[str, Any]] = None

    if status == "success":
        try:
            universe = get_company_universe(company_limit)
            stages_ok += 1

            raw = collect_raw_records(universe, args.run_date, args.frequency, backfill_years)
            stages_ok += 1

            curated = normalize_records(raw)
            stages_ok += 1

            quality_report = run_quality_checks(curated)
            stages_ok += 1

            loaded_rows = load_curated(curated, dry_run=args.dry_run)
            stages_ok += 1

            print(f"[run_id={run_id}] loaded_rows={loaded_rows} quality={quality_report}")

        except Exception as e:
            status = "failed"
            err = f"pipeline_error: {repr(e)}"
            stages_failed += 1
            print(f"[run_id={run_id}] ERROR: {err}", file=sys.stderr)

    end = utc_now_iso()

    # run log
    run_log_path = log_cfg.get("run_log_path", "logs/pipeline_runs.jsonl")
    if not os.path.isabs(run_log_path):
        run_log_path = os.path.join(base_dir, run_log_path)

    record = RunLog(
        run_id=run_id,
        start_time_utc=start,
        end_time_utc=end,
        run_date=args.run_date,
        frequency=args.frequency,
        backfill_years=int(backfill_years),
        company_limit=int(company_limit),
        stages_ok=int(stages_ok),
        stages_failed=int(stages_failed),
        status=status,
        error=err,
        notes=notes,
    )
    write_jsonl(run_log_path, asdict(record))
    print(f"[run_id={run_id}] run_log_written_to={run_log_path}")

    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
