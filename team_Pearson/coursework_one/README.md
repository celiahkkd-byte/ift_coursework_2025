# Team Pearson - Coursework One (CW1)

## Branch
Work on: `feature/coursework_one_Team_04_Pearson`

## Folder rule
All deliverables must live under:
`team_Pearson/coursework_one/`

Do not commit changes outside this folder (e.g., `000.Database`).

## Quickstart (local)
From repository root:

1) If Poetry is installed:

```bash
cd team_Pearson/coursework_one
poetry install
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
```

2) Minimal run without Poetry (for skeleton smoke check):

```bash
cd team_Pearson/coursework_one
python Main.py --run-date 2026-02-14 --frequency daily --dry-run
python -m pytest -q test/test_smoke.py
```

## CLI parameters
- `--run-date` (required): decision date in `YYYY-MM-DD`
- `--frequency` (required): `daily|weekly|monthly|quarterly`
- `--backfill-years` (optional): history length, default from config
- `--company-limit` (optional): universe size cap, default from config
- `--dry-run` (optional): run pipeline without final load

## Current status
This is an integration skeleton for role 4. Pipeline stages are currently mock stubs and will be replaced by module implementations from other roles.

## Integration contracts (for roles 3/5/6/7/8)
- `modules.db.get_company_universe(company_limit: int) -> list[str]`
- `modules.input.extract_source_a(company_ids, run_date, backfill_years, frequency) -> list[dict]`
- `modules.input.extract_source_b(company_ids, run_date, backfill_years, frequency) -> list[dict]`
- `modules.output.normalize_records(records) -> list[dict]`
- `modules.output.run_quality_checks(records) -> dict`
- `modules.output.load_curated(records, dry_run: bool) -> int`
