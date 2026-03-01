# Data Dictionary

This document reflects the current implemented schema in `team_Pearson/coursework_one/sql/init.sql` and the current pipeline behavior.

## 1. Table: `systematic_equity.company_static`

Upstream universe table used by the pipeline (`modules/db/universe.py`).

| Column Name | Type | Description | Notes |
| --- | --- | --- | --- |
| `symbol` | TEXT / VARCHAR | Company ticker | Universe key used by extractors |
| `company_name` | TEXT | Company name | Optional in pipeline logic |
| `country` | TEXT | Country code/name | Used by country allowlist filter |
| `sector` | TEXT | Sector name | Optional metadata |

## 2. Table: `systematic_equity.factor_observations`

Curated long-table factor store.

| Column Name | Type | Description | Notes |
| --- | --- | --- | --- |
| `id` | SERIAL | Surrogate primary key | Auto-increment |
| `symbol` | VARCHAR(50) | Company ticker | Required |
| `observation_date` | DATE | Factor date | Required |
| `factor_name` | VARCHAR(50) | Factor identifier | Required |
| `factor_value` | NUMERIC(18,6) | Factor numeric value | Nullable |
| `source` | VARCHAR(50) | Data source or transform stage | e.g. `alpha_vantage`, `yfinance`, `extractor_b`, `factor_transform` |
| `metric_frequency` | VARCHAR(20) | Frequency tag | Check constraint: `daily/weekly/monthly/quarterly/annual/unknown` |
| `source_report_date` | DATE | Source report/reference date | Nullable |
| `updated_at` | TIMESTAMP | Row update timestamp | Default `CURRENT_TIMESTAMP` |

Constraints and indexes:
- Unique key: `UNIQUE(symbol, observation_date, factor_name)` (`uniq_observation`)
- Index: `idx_factor_obs_symbol` on `symbol`
- Index: `idx_factor_obs_observation_date` on `observation_date`

Current atomic factors (input/ingest stage):
- `adjusted_close_price`
- `daily_return` (log return: `ln(price_t / price_t-1)`)
- `dividend_per_share`
- `news_sentiment_daily`
- `news_article_count_daily`

Current final factors (transform stage):
- `momentum_1m`
- `volatility_20d`
- `dividend_yield`
- `pb_ratio`
- `debt_to_equity`
- `ebitda_margin`
- `sentiment_30d_avg`
- `article_count_30d`

## 3. Table: `systematic_equity.financial_observations`

Atomic fundamentals store with financial-report semantics.

| Column Name | Type | Description | Notes |
| --- | --- | --- | --- |
| `id` | SERIAL | Surrogate primary key | Auto-increment |
| `symbol` | VARCHAR(50) | Company ticker | Required |
| `report_date` | DATE | Financial report period-end | Required |
| `metric_name` | VARCHAR(100) | Financial metric identifier | Required |
| `metric_value` | NUMERIC(18,6) | Metric numeric value | Nullable |
| `currency` | VARCHAR(16) | Currency code | Nullable; often `USD`/`UNKNOWN` |
| `period_type` | VARCHAR(20) | Financial period type | Check constraint: `annual/quarterly/ttm/snapshot/unknown` |
| `metric_definition` | VARCHAR(50) | Value definition/semantic tag | Check: `provider_reported/normalized/estimated/unknown` |
| `source` | VARCHAR(50) | Data source | e.g. `alpha_vantage`, `yfinance` |
| `as_of` | DATE | Observation/snapshot date | Nullable |
| `updated_at` | TIMESTAMP | Row update timestamp | Default `CURRENT_TIMESTAMP` |

Constraints and indexes:
- Unique key: `UNIQUE(symbol, report_date, metric_name)` (`uniq_financial_observation`)
- Index: `idx_financial_obs_symbol` on `symbol`
- Index: `idx_financial_obs_report_date` on `report_date`

Current financial atomic metrics:
- `total_debt`
- `book_value`
- `total_shareholder_equity`
- `shares_outstanding`
- `enterprise_ebitda`
- `enterprise_revenue`

## 4. Table: `systematic_equity.pipeline_runs`

Primary pipeline audit table (source of truth for run-level traceability).

| Column Name | Type | Description | Notes |
| --- | --- | --- | --- |
| `run_id` | VARCHAR(64) | Unique pipeline run ID | Primary key |
| `run_date` | DATE | Business run date from CLI | Required |
| `started_at` | TIMESTAMPTZ | UTC start time | Required |
| `finished_at` | TIMESTAMPTZ | UTC finish time | Nullable until finished |
| `status` | VARCHAR(20) | Run status | Check: `running/success/failed` |
| `frequency` | VARCHAR(20) | CLI frequency | Nullable |
| `backfill_years` | INT | Backfill depth | Nullable |
| `company_limit` | INT | Universe limit | Nullable |
| `enabled_extractors` | TEXT | Active extractor list | e.g. `source_a,source_b` |
| `rows_written` | INT | Number of rows written | Default `0` |
| `error_message` | TEXT | Error summary | Nullable |
| `error_traceback` | TEXT | Error traceback | Nullable |
| `notes` | TEXT | Scheduling/provider notes | Nullable |
| `created_at` | TIMESTAMPTZ | Insert timestamp | Default `CURRENT_TIMESTAMP` |
| `updated_at` | TIMESTAMPTZ | Update timestamp | Default `CURRENT_TIMESTAMP` |

Supporting index:
- `idx_pipeline_runs_run_date`
- `idx_pipeline_runs_status`

## 5. File-Based Audit Mirror

Secondary debug mirror:
- `logs/pipeline_runs.jsonl`

This mirror is for local troubleshooting only; PostgreSQL `systematic_equity.pipeline_runs` is the authoritative audit source.
