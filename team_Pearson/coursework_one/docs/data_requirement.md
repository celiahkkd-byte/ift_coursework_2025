# Data Requirements Log
**Strategy:** Quality, Dividend & Sentiment Composite Strategy
**History Requirement:** Minimum 5 years backfill
**Query Requirement:** Must support retrieval by company and by year

---

## 1. Dividend Yield

| Field | Specification |
|------|--------------|
| Metric Name | Dividend Yield |
| Raw Fields | Dividend Per Share (DPS), Adjusted Close Price |
| Origin Source (Input) | External API (`yfinance`) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Monthly (computed using latest available dividend at month-end) |
| History | ≥ 5 years |
| Calculation Logic | Dividend Yield = (Trailing 12-Month Total DPS) / Price |

### Missing / Error Tolerance & Quality Rules
- **Look-ahead Bias Prevention:** Price must be queried strictly backward-looking. Use the exact date's close. If the exact date falls on a weekend/holiday, fall back to the most recent trading day, **maximum 3 trading days prior (-3 to 0 days)**. Future prices (+1 to +3 days) are strictly forbidden.
- **Missing DPS Tolerance:** If dividend history is missing or no dividends were declared within the last 12 months, do NOT drop the observation. Set `Dividend Yield = 0.0`.
- **Missing Price Tolerance:** If `Adjusted Close Price` is missing, NaN, or ≤ 0 after the 3-day backward look, **DROP** the observation for that specific date to avoid zero-division errors.
- **Quality Auditing:** Log a warning (`flag_stale_price = True`) if a price older than 1 trading day is used.

---

## 2. EBITDA Margin (Profitability Factor)

| Field | Specification |
|------|--------------|
| Metric Name | EBITDA Margin |
| Raw Fields | `enterprise_ebitda`, `enterprise_revenue`, `end_date` |
| Origin Source (Input) | Internal PostgreSQL (`systematic_equity` static tables) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Quarterly/Annual (aligned with internal table updates) |
| History | ≥ 5 years |
| Calculation Logic | EBITDA Margin = `enterprise_ebitda` / `enterprise_revenue` |

### Missing / Error Tolerance & Quality Rules
- **Negative Revenue:** If `enterprise_revenue` ≤ 0, **DROP** the observation (margins on zero/negative revenue are mathematically meaningless).
- **Missing Values:** If either `enterprise_ebitda` or `enterprise_revenue` is NULL/NaN, **DROP** the observation. Do not attempt to impute EBITDA.
- **Staleness Limit:** Data from the internal table must be forward-filled on a daily/monthly basis for portfolio alignment. The maximum allowed staleness from the internal `end_date` is **12 months**.
- **Expiration:** If the latest available `end_date` is older than 12 months relative to the calculation date, **DROP** the observation and log a `Data_Expired` flag.

---

## 3. Debt/Equity Ratio (Financial Health Factor)

| Field | Specification |
|------|--------------|
| Metric Name | Debt/Equity |
| Raw Fields | Total Debt (Short-term + Long-term), `book_value` |
| Origin Source (Input) | **Mixed:** External API (`yfinance` for Debt) + Internal PostgreSQL (`book_value`) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Quarterly |
| History | ≥ 5 years |
| Calculation Logic | Debt/Equity = Total Debt / `book_value` |

### Missing / Error Tolerance & Quality Rules
- **Missing Debt Fallback:** If `Total Debt` is missing directly from the API, attempt to calculate it as `Short-term Debt + Long-term Debt`. If both are missing, **DROP** the observation.
- **Negative Equity:** If internal `book_value` ≤ 0, **DROP** the observation. Highly distressed companies with negative equity produce misleading D/E ratios.
- **Cross-Source Staleness Limit:** External Debt and Internal Book Value may be published on different dates. Both components may be forward-filled up to a maximum of **9 months** from their respective report dates.
- **Interpolation:** Strict **NO**. Step-forward fill only.

---

## 4. Price-to-Book Ratio (P/B) (Valuation Factor)

| Field | Specification |
|------|--------------|
| Metric Name | P/B Ratio |
| Raw Fields | Adjusted Close Price, `outstanding_shares`, `book_value` |
| Origin Source (Input) | **Mixed:** External API (`Price`) + Internal PostgreSQL (`outstanding_shares`, `book_value`) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Monthly |
| History | ≥ 5 years |
| Calculation Logic | P/B = (Price * `outstanding_shares`) / `book_value` |

### Missing / Error Tolerance & Quality Rules
- **Look-ahead Bias Prevention:** Price must strictly utilize the [-3 to 0 days] backward-looking rule.
- **Negative Equity:** If internal `book_value` ≤ 0, **DROP** the observation.
- **Missing Shares:** If `outstanding_shares` is missing, NaN, or ≤ 0, **DROP** the observation (market cap cannot be calculated).
- **Staleness Limit:** Internal fundamental data (`book_value`, `outstanding_shares`) may be forward-filled up to **12 months**.
- **Extreme Values Cap:** Cap P/B ratios at the 99th percentile (e.g., P/B > 100) to prevent data anomalies from skewing Z-score calculations in Coursework 2.

---

## 5. News Sentiment Score (Alternative Risk Factor)

| Field | Specification |
|------|--------------|
| Metric Name | News Sentiment |
| Raw Fields | Article Sentiment Score, Timestamp |
| Origin Source (Input) | External API (e.g., Alpha Vantage `NEWS_SENTIMENT` or NewsAPI) |
| Target Storage (Output) | MinIO (Raw JSON) → PostgreSQL (`factor_observations`) |
| Frequency | Daily (aggregated to monthly for portfolio rebalancing) |
| History | ≥ 5 years (where available depending on API limits) |
| Calculation Logic | Simple Average of sentiment scores over a rolling 30-day window. |

### Missing / Error Tolerance & Quality Rules
- **Zero News Fallback:** If NO news articles are found for a given company within the trailing 30-day window, **DO NOT DROP** the observation. Assign a neutral sentiment score of **0.0**.
- **Data Capping:** Hard cap all computed sentiment scores to a range of `[-1.0, 1.0]`.
- **Audit Logging:** The system must record `article_count_30d` as a secondary metadata column alongside the score to distinguish between a "0.0 due to no news" vs a "0.0 due to mixed news".

---

# System-Level Acceptance Criteria (Definition of Done)

The pipeline and infrastructure must pass the following verifiable automated criteria before pull requests can be merged.

### 1. Data Coverage & Integrity Tests (`pytest`)
- **Historical Depth:** Pipeline must successfully backfill and persist ≥ 5 years of data for at least 3 test companies without throwing unhandled exceptions.
- **Missing Data Enforcement:** Unit tests must inject mocked stale data (e.g., Book Value > 12 months old) and explicitly assert that the ETL pipeline drops the observation.
- **Test Coverage Red Line:** The `pytest` suite running over the `transform` and `quality` modules must achieve a minimum of **80% code coverage**.

### 2. Query Capability & Indexing
- **EAV / Long Table Pattern:** The `factor_observations` schema must be designed as a "long table" (e.g., `company_id`, `as_of_date`, `factor_name`, `factor_value`) rather than a wide table, satisfying the requirement that *adding a new metric must not require a schema ALTER operation*.
- **Performance:** B-Tree indexes must be applied to `company_id` and `as_of_date`. The database must support sub-second query execution times for:
  1. Retrieving all metrics for a single `company_id` over a 5-year period.
  2. Retrieving a specific `factor_name` across all companies for a given calendar year.

### 3. Pipeline Robustness & Fault Tolerance
- **Dynamic Universe:** The pipeline must dynamically query `systematic_equity.company_static` at runtime. Adding or removing a symbol from this table must immediately reflect in the pipeline's execution loop without requiring codebase changes.
- **Idempotency & Uniqueness:** The pipeline must be idempotent. Rerunning the pipeline for the same date range must not duplicate data. PostgreSQL must utilize a composite Unique Constraint (`company_id`, `factor_name`, `as_of_date`) combined with an `INSERT ... ON CONFLICT DO UPDATE` (Upsert) strategy.
- **Non-Blocking Execution:** If the API request for `company A` fails (e.g., HTTP 404 or 500), the pipeline must catch the exception, log the error trace to a `pipeline_runs` audit table, and seamlessly continue processing `company B`.

### 4. Quality Auditability
- **Lineage Tracing:** Every row in the curated PostgreSQL table must include a `run_id` or `updated_at` timestamp linking it back to the specific execution batch that fetched the raw data from MinIO.
