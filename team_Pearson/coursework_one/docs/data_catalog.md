# Data Catalog

This catalog lists implemented datasets, owners, and storage locations.

| Dataset Name | Type | Storage | Description | Owner / Role |
| --- | --- | --- | --- | --- |
| `company_static` | Structured table | PostgreSQL `systematic_equity.company_static` | Dynamic investable universe (symbols and metadata). | Role 5 |
| `source_a_raw_pricing_fundamentals` | Raw JSON | MinIO `raw/source_a/pricing_fundamentals/...` | Source A raw payloads (Alpha Vantage primary, yfinance fallback). | Role 6 |
| `source_b_raw_news` | Raw JSONL | MinIO `raw/source_b/news/run_date=.../year=.../month=.../symbol=...jsonl` | Source B raw article text payloads (deduplicated by URL or `title+time_published`). | Role 7 |
| `financial_observations` | Structured long table | PostgreSQL `systematic_equity.financial_observations` | Atomic financial metrics with period semantics (`symbol/report_date/metric/value/currency/period_type`). | Role 8 |
| `factor_observations` | Structured long table | PostgreSQL `systematic_equity.factor_observations` | Atomic and final factors in EAV format (`symbol/date/factor/value`). | Role 8 |
| `pipeline_runs` | Structured audit table | PostgreSQL `systematic_equity.pipeline_runs` | Primary run-level audit trail (`running/success/failed`, context, row counts, errors). | Role 8 |
| `pipeline_runs_jsonl` | JSONL log | Local file `logs/pipeline_runs.jsonl` | Secondary debug mirror of run logs (non-authoritative). | Role 8 |

## Notes

- Source A market atomic factors currently include `adjusted_close_price`, `daily_return`, and `dividend_per_share`.
- Financial atomic metrics (`book_value`, `total_shareholder_equity`, `shares_outstanding`, `total_debt`, `enterprise_ebitda`, `enterprise_revenue`) are persisted to `financial_observations`.
- Source B alternative atomic factors include `news_sentiment_daily` and `news_article_count_daily`.
- Final factor computation is handled by `modules/transform/factors.py` and persisted to `factor_observations` (including recomputed technical factors `momentum_1m` and `volatility_20d`).
- MinIO paths intentionally include `run_date` for traceability and reproducibility.
