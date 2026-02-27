import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


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
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_jsonl(path: str, record: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def apply_env_defaults_from_config(cfg: Dict[str, Any]) -> None:
    """Use config values as env fallbacks, while keeping env as source of truth."""
    db_cfg = cfg.get("database") or {}
    minio_cfg = cfg.get("minio") or {}

    mapping = {
        "POSTGRES_HOST": db_cfg.get("host"),
        "POSTGRES_PORT": db_cfg.get("port"),
        "POSTGRES_DB": db_cfg.get("name"),
        "POSTGRES_USER": db_cfg.get("user"),
        "POSTGRES_PASSWORD": db_cfg.get("password"),
        "POSTGRES_SCHEMA": db_cfg.get("schema"),
        "MINIO_ENDPOINT": minio_cfg.get("endpoint"),
        "MINIO_ACCESS_KEY": minio_cfg.get("access_key"),
        "MINIO_SECRET_KEY": minio_cfg.get("secret_key"),
        "MINIO_BUCKET": minio_cfg.get("bucket"),
    }
    for key, value in mapping.items():
        if os.getenv(key) in (None, "") and value not in (None, ""):
            os.environ[key] = str(value)


def get_window(run_date: str, frequency: str) -> tuple[str, str]:
    """Return [start_date, end_date] for the requested scheduling frequency."""
    end = datetime.strptime(run_date, "%Y-%m-%d").date()

    if frequency == "daily":
        start = end
    elif frequency == "weekly":
        start = end - timedelta(days=6)
    elif frequency == "monthly":
        start = end.replace(day=1)
    elif frequency == "quarterly":
        quarter_start_month = ((end.month - 1) // 3) * 3 + 1
        start = date(end.year, quarter_start_month, 1)
    elif frequency == "annual":
        start = date(end.year, 1, 1)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")

    return start.isoformat(), end.isoformat()


def collect_raw_records(
    symbols: List[str],
    run_date: str,
    frequency: str,
    backfill_years: int,
    enabled_extractors: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Merge records from the currently integrated source modules.

    In CI/unit tests, set env var `CW1_TEST_MODE=1` to bypass external extractors.
    """
    if os.getenv("CW1_TEST_MODE") == "1":
        out: List[Dict[str, Any]] = []
        for symbol in symbols:
            out.append(
                {
                    "symbol": symbol,
                    "observation_date": run_date,
                    "factor_name": "test_factor",
                    "factor_value": 1.0,
                    "source": "test_mode",
                    "metric_frequency": frequency,
                    "source_report_date": run_date,
                }
            )
        return out

    selected = enabled_extractors or ["source_a"]
    normalized_selected = {str(x).strip().lower() for x in selected}
    records: List[Dict[str, Any]] = []

    # Lazy imports keep local test/dev fast and avoid heavy optional dependencies.
    if "source_a" in normalized_selected:
        try:
            from modules.input.extract_source_a import extract_source_a

            records.extend(
                extract_source_a(symbols, run_date, backfill_years, frequency, config=config)
            )
        except Exception as exc:
            print(f"[extractor=source_a] failed: {exc!r}", file=sys.stderr)

    if "source_b" in normalized_selected:
        try:
            from modules.input.extract_source_b import extract_source_b

            records.extend(
                extract_source_b(symbols, run_date, backfill_years, frequency, config=config)
            )
        except Exception as exc:
            print(f"[extractor=source_b] failed: {exc!r}", file=sys.stderr)

    return records


def summarize_provider_usage(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize provider usage by symbol based on total_debt marker rows."""
    symbol_provider: Dict[str, str] = {}
    for rec in records:
        if rec.get("factor_name") != "total_debt":
            continue
        symbol = str(rec.get("symbol") or "").strip()
        source = str(rec.get("source") or "").strip().lower()
        if symbol and source:
            symbol_provider[symbol] = source

    counts: Dict[str, int] = {}
    for provider in symbol_provider.values():
        counts[provider] = counts.get(provider, 0) + 1
    return counts


def scheduling_stub(frequency: str) -> str:
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
    p.add_argument("--run-date", required=True, help="Run date in YYYY-MM-DD.")
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
        "--dry-run",
        action="store_true",
        help="Run pipeline without loading to storage (still runs transforms/quality).",
    )
    p.add_argument(
        "--enabled-extractors",
        default=None,
        help="Comma-separated extractors to run, e.g. source_a,source_b (default from config).",
    )
    return p.parse_args()


def resolve_paths(base_dir: str, config_path: str) -> str:
    if os.path.isabs(config_path):
        return config_path
    return os.path.join(base_dir, config_path)


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    args = parse_args()

    cfg_path = resolve_paths(base_dir, args.config)
    cfg = load_yaml(cfg_path)
    apply_env_defaults_from_config(cfg)

    pipeline_cfg = cfg.get("pipeline") or {}
    log_cfg = cfg.get("logging") or {}
    configured_extractors = pipeline_cfg.get("enabled_extractors", ["source_a"])

    if args.enabled_extractors:
        enabled_extractors = [
            x.strip().lower() for x in args.enabled_extractors.split(",") if x.strip()
        ]
    elif isinstance(configured_extractors, list):
        enabled_extractors = [
            str(x).strip().lower() for x in configured_extractors if str(x).strip()
        ]
    else:
        enabled_extractors = ["source_a"]

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

    try:
        notes = scheduling_stub(args.frequency)
        window_start, window_end = get_window(args.run_date, args.frequency)
        notes = f"{notes}; window_start={window_start}; window_end={window_end}"
        stages_ok += 1
    except Exception as e:
        status = "failed"
        err = f"scheduling_stub_error: {repr(e)}"
        stages_failed += 1

    loaded_rows = 0
    quality_report: Optional[Dict[str, Any]] = None
    provider_usage: Dict[str, int] = {}

    if status == "success":
        try:
            # Lazy imports so unit tests can import Main without DB drivers installed.
            from modules.db.universe import get_company_universe
            from modules.output import load_curated, normalize_records, run_quality_checks

            universe_cfg = cfg.get("universe") or {}
            country_allowlist = universe_cfg.get("country_allowlist")
            universe = get_company_universe(company_limit, country_allowlist=country_allowlist)
            stages_ok += 1

            raw = collect_raw_records(
                universe,
                args.run_date,
                args.frequency,
                backfill_years,
                enabled_extractors=enabled_extractors,
                config=cfg,
            )
            provider_usage = summarize_provider_usage(raw)
            if provider_usage:
                notes = f"{notes}; provider_usage={json.dumps(provider_usage, sort_keys=True)}"
            stages_ok += 1

            curated = normalize_records(raw)
            stages_ok += 1

            quality_report = run_quality_checks(curated)
            stages_ok += 1

            loaded_rows = load_curated(curated, dry_run=args.dry_run)
            stages_ok += 1

            fallback_count = provider_usage.get("yfinance", 0)
            fallback_used = "yes" if fallback_count > 0 else "no"
            print(
                f"[run_id={run_id}] loaded_rows={loaded_rows} "
                f"quality={quality_report} fallback_used={fallback_used} "
                f"fallback_count={fallback_count}"
            )

        except Exception as e:
            status = "failed"
            err = f"pipeline_error: {repr(e)}"
            stages_failed += 1
            print(f"[run_id={run_id}] ERROR: {err}", file=sys.stderr)

    end = utc_now_iso()

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
