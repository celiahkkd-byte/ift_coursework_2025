# Data Lineage

This document describes the implemented end-to-end data flow from source APIs to curated factors.

## 1. End-to-End Flow

1. Universe load:
- Read symbols from PostgreSQL `systematic_equity.company_static` (dynamic universe).
- Optional country/symbol filtering policy is applied in extractor filters.

2. Source A (structured market/fundamentals):
- Primary provider: Alpha Vantage
- Fallback provider: yfinance
- Raw payload archived to MinIO:
  - `raw/source_a/pricing_fundamentals/run_date=YYYY-MM-DD/year=YYYY/symbol=XXX.json`
- Atomic rows produced into pipeline stream:
  - Market/technical atomic (`adjusted_close_price`, `daily_return`, `dividend_per_share`, `momentum_1m`, `volatility_20d`) -> `factor_observations`
  - Financial atomic (`book_value`, `shares_outstanding`, `total_debt`, `enterprise_ebitda`, `enterprise_revenue`) -> `financial_observations`

3. Source B (unstructured news text):
- Alpha Vantage `NEWS_SENTIMENT` is used for article text ingestion.
- Raw payload archived to MinIO as JSONL (symbol x month):
  - `raw/source_b/news/run_date=YYYY-MM-DD/year=YYYY/month=MM/symbol=XXX.jsonl`
- Deduplication rule: URL first, fallback to `title+time_published`.
- Alternative atomic rows:
  - `news_sentiment_daily` (daily sentiment)
  - `news_article_count_daily` (daily article count)

4. Normalize + quality + load:
- Records are normalized to long-table schema.
- Quality checks validate required columns, frequency values, duplicates, and finite numeric values.
- Upsert market/alternative atomic + final factors into `systematic_equity.factor_observations` via unique constraint (`symbol`, `observation_date`, `factor_name`).
- Upsert financial atomic into `systematic_equity.financial_observations` via unique constraint (`symbol`, `report_date`, `metric_name`).

5. Final-factor transform stage:
- Read market/alternative atomic from `factor_observations` and financial atomic from `financial_observations`.
- Compute final factors in `modules/transform/factors.py`.
- Write final factors back to `factor_observations`.

6. Audit:
- Primary run audit written to PostgreSQL `systematic_equity.pipeline_runs`.
- Secondary local mirror written to `logs/pipeline_runs.jsonl`.

## 2. Factor-Level Lineage

| Final Factor | Atomic Inputs | Core Rule | Output |
| --- | --- | --- | --- |
| `dividend_yield` | `dividend_per_share`, `adjusted_close_price` | TTM DPS / backward-looking price (month-end, max 3-day lookback) | `factor_observations` |
| `pb_ratio` | `adjusted_close_price`, `shares_outstanding`, `book_value` | `(price * shares) / book_value`, positive checks, cap at 100 | `factor_observations` |
| `debt_to_equity` | `total_debt`, `book_value` | `total_debt / book_value`, quarterly, stale limit 270 days | `factor_observations` |
| `ebitda_margin` | `enterprise_ebitda`, `enterprise_revenue` | `ebitda / revenue`, revenue must be positive | `factor_observations` |
| `sentiment_30d_avg` | `news_sentiment_daily` | daily mean->fill missing dates with `0.0`->rolling `30D` mean, capped `[-1,1]` | `factor_observations` |
| `article_count_30d` | `news_article_count_daily` | daily count->fill missing dates with `0.0`->rolling `30D` sum | `factor_observations` |

## 3. Storage and Partitioning

MinIO raw layer:
- Source A: one object per `symbol x run_date`.
- Source B: one object per `symbol x month` under each run date.

PostgreSQL curated layer:
- Layered long tables:
  - `systematic_equity.factor_observations` (market/alternative atomic + final factors)
  - `systematic_equity.financial_observations` (financial atomic)
- Query optimized by:
  - symbol index
  - date indexes (`observation_date` / `report_date`)
  - unique business keys by table

## 4. Reproducibility Notes

- `run_date`, `frequency`, `backfill_years`, `company_limit`, and `enabled_extractors` are recorded in `pipeline_runs`.
- Raw payloads in MinIO include `run_date` in path to support replay/audit.
- Idempotent upsert prevents duplicate factor rows across repeated runs for the same business key.
