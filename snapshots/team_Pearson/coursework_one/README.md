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
Mandatory rule:
- Run `docker compose ...` only in repository root `ift_coursework_2025/`.
- Do not run `docker compose` inside `team_Pearson/coursework_one/`.

Use the repository root `docker-compose.yml` as shared infra. From repo root:

```bash
cd ift_coursework_2025
docker compose up -d postgres_db mongo_db miniocw minio_client_cw
```

## Standard run sequence (copy/paste)
Run exactly in this order:

```bash
# 1) Start infra in repo root
cd ift_coursework_2025
docker compose up -d postgres_db mongo_db miniocw minio_client_cw

# 2) Run app and tests in coursework_one
cd team_Pearson/coursework_one
poetry install
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
poetry run pytest tests -q
```

If universe tables are missing, seed from the teacher SQLite file (no edits to `000.Database`):

```bash
cd team_Pearson/coursework_one
poetry run python scripts/seed_universe_from_sqlite.py
```

Services and local ports from current compose:
- PostgreSQL: `localhost:5439` -> container `5432`
- MongoDB: `localhost:27019` -> container `27017`
- MinIO API: `localhost:9000` (Console: `localhost:9001`)

Docker-aligned defaults used by this project (single source: repo root `docker-compose.yml`):
- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5439`
- `POSTGRES_DB=postgres` (compose does not set `POSTGRES_DB`, default DB is `postgres`)
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `MONGO_HOST=localhost`
- `MONGO_PORT=27019`
- `MONGO_DB=admin` (compose does not configure Mongo auth)
- `MINIO_ENDPOINT=localhost:9000`
- `MINIO_ACCESS_KEY=ift_bigdata`
- `MINIO_SECRET_KEY=minio_password`
- `MINIO_BUCKET=csreport`

MinIO bucket initialization behavior from compose:
- `minio_client_cw` runs `mc rm -r --force minio/csreport` then `mc mb minio/csreport`.
- This means bucket `csreport` is recreated by compose bootstrap (not manually created in app setup docs).

Configuration precedence:
- Environment variables are the source of truth.
- `config/conf.yaml` provides fallback defaults when env vars are missing.

Environment template for local runtime:
- `team_Pearson/coursework_one/.env.example`

If needed, create your local env file:

```bash
cd team_Pearson/coursework_one
cp .env.example .env
```

## CLI parameters
- `--run-date` (required): decision date in `YYYY-MM-DD`
- `--frequency` (required): `daily|weekly|monthly|quarterly|annual`
- `--backfill-years` (optional): history length, default from config
- `--company-limit` (optional): universe size cap, default from config
- `--dry-run` (optional): run pipeline without final load
- `--enabled-extractors` (optional): comma-separated extractor list, e.g. `source_a` or `source_a,source_b`

## Extractor switches
Default extractor selection is configured in:
- `config/conf.yaml` -> `pipeline.enabled_extractors`
- `config/conf.yaml.example` -> `pipeline.enabled_extractors`

Default is:
```yaml
pipeline:
  enabled_extractors:
    - source_a
```

CLI can override config:
```bash
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run --enabled-extractors source_a,source_b
```

## Source A provider strategy
`source_a` uses a dual-provider design:
- Primary provider: Alpha Vantage (paid API)
- Fallback provider: yfinance (enabled when Alpha Vantage fails)
- Optional replay cache: MinIO raw payload reuse via `source_a.use_cache`

Config keys:
```yaml
api:
  alpha_vantage_key: "YOUR_KEY"
source_a:
  primary_source: alpha_vantage
  enable_yfinance_fallback: true
  use_cache: true
```

Implemented technical factors (daily):
- `momentum_1m`: `(Price_t / Price_{t-20}) - 1`
- `volatility_20d`: rolling 20-day standard deviation of daily returns
- Rule: if history has fewer than 20 trading days, these observations are dropped.

## Current status
This is an integration skeleton for role 4. Pipeline stages are currently mock stubs and will be replaced by module implementations from other roles.

Current delivery focus:
- Structured pipeline (`source_a`) is integrated end-to-end (extract -> normalize -> quality -> upsert).
- `source_b` is kept as a pluggable staged module and can be enabled later without changing downstream contracts.

## Mixed-frequency run examples
```bash
cd team_Pearson/coursework_one
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
poetry run python Main.py --run-date 2026-02-01 --frequency monthly --dry-run
poetry run python Main.py --run-date 2026-12-31 --frequency annual --dry-run
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run --enabled-extractors source_a,source_b
```

## Integration contracts (for roles 3/5/6/7/8)
- `modules.db.get_company_universe(company_limit: int) -> list[str]`
- `modules.input.extract_source_a(symbols, run_date, backfill_years, frequency, config=None) -> list[dict]`
- `modules.input.extract_source_b(symbols, run_date, backfill_years, frequency, config=None) -> list[dict]`
- `modules.output.normalize_records(records) -> list[dict]`
- `modules.output.run_quality_checks(records) -> dict`
- `modules.output.load_curated(records, dry_run: bool) -> int`

## Extractor B staged design
`extract_source_b` is intentionally pluggable and split into two stages:
1. `ingest_source_b_raw(...)`: raw collection and lake storage hook (currently stubbed).
2. `transform_source_b_features(...)`: converts raw payloads to normalized records (currently stubbed).

This allows long-running unstructured ingestion to be decoupled from daily pipeline/test runs while keeping downstream schema stable.

## Output and Infra Ownership
- Role 3 (primary): `modules/output/load.py` and SQL persistence rules (e.g., `sql/init.sql` with upsert/index/constraints)
- Role 5 (support): database-schema compatibility checks for SQL changes
- Role 4 (primary): integration-safe management of shared runtime config (`docker-compose.yml`, `.env` conventions)

This split is used to reduce merge conflicts on shared infra files while keeping storage logic owned by the output/database roles.

## Pre-submit validation checklist
Run from `team_Pearson/coursework_one`:

```bash
poetry run pytest -q
# coverage threshold is enforced by pytest config (>=80%)
poetry run pytest
poetry run bandit -r modules Main.py
VENV_PATH=$(poetry env info -p) && HOME=/tmp "$VENV_PATH/bin/safety" check -r poetry.lock
cd docs/sphinx && poetry run make html
```

Docs entry point after build:
- `docs/sphinx/build/html/index.html`
