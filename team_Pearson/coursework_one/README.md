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
python -m pytest tests -q
```

## Container bootstrap (minimal)
Use the repository root `docker-compose.yml` as shared infra. From repo root:

```bash
docker compose up -d postgres_db mongo_db miniocw
```

Services and local ports from current compose:
- PostgreSQL: `localhost:5439`
- MongoDB: `localhost:27019`
- MinIO API: `localhost:9000` (Console: `localhost:9001`)

Environment template for local runtime:
- `team_Pearson/coursework_one/.env.example`

If needed, create your local env file:

```bash
cd team_Pearson/coursework_one
cp .env.example .env
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

## Output and Infra Ownership
- Role 3 (primary): `modules/output/load.py` and SQL persistence rules (e.g., `sql/init.sql` with upsert/index/constraints)
- Role 5 (support): database-schema compatibility checks for SQL changes
- Role 4 (primary): integration-safe management of shared runtime config (`docker-compose.yml`, `.env` conventions)

This split is used to reduce merge conflicts on shared infra files while keeping storage logic owned by the output/database roles.
