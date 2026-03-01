# Architecture Overview

## Objective
Deliver a runnable CW1 data pipeline where structured inputs can be extracted, normalized, quality-checked, and upserted into PostgreSQL with stable keys.

## Pipeline stages
1. Universe retrieval from `systematic_equity.company_static`.
2. Extractors selected by `enabled_extractors` (`source_a` by default).
3. Normalize records to a long-format schema.
4. Run quality checks (missing fields, duplicates, frequency validity).
5. Upsert into `systematic_equity.factor_observations`.
6. Write run metadata to JSONL logs.

## Storage design
- **Raw lake path (source_a):** `raw/source_a/pricing_fundamentals/run_date={YYYY-MM-DD}/year={YYYY}/symbol={SYMBOL}.json`
- **Curated table:** `systematic_equity.factor_observations`
- **Uniqueness:** `(symbol, observation_date, factor_name)`

## Fault tolerance
- Extractor failures are isolated and logged.
- `CW1_TEST_MODE=1` bypasses external dependencies for deterministic test execution.

## Extensibility
`source_b` is implemented as a pluggable two-stage module:
- ingest raw payloads
- transform to feature records

This allows delayed integration without changing downstream normalize/load logic.
