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
| Origin Source (Input) | External API (`Alpha Vantage`) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Monthly (computed using latest available dividend at month-end) |
| History | ≥ 5 years |
| Calculation Logic | Dividend Yield = (Trailing 12-Month Total DPS) / Price |

### Missing / Error Tolerance & Quality Rules
- **Look-ahead Bias Prevention:** Price must be queried strictly backward-looking. Use the exact date's close. If the exact date falls on a weekend/holiday, fall back to the most recent trading day, **maximum 3 trading days prior (-3 to 0 days)**. Future prices (+1 to +3 days) are strictly forbidden.
- **Missing DPS Tolerance:** If dividend history is missing or no dividends were declared within the last 12 months, do NOT drop the observation. Set `Dividend Yield = 0.0`.
- **Missing Price Tolerance:** If `Adjusted Close Price` is missing, NaN, or ≤ 0 after the 3-day backward look, **DROP** the observation for that specific date to avoid zero-division errors.
- **Quality Auditing:** Log stale-price usage in run notes/logs when fallback price date is older than 1 trading day.

---

## 2. EBITDA Margin (Profitability Factor)

| Field | Specification |
|------|--------------|
| Metric Name | EBITDA Margin |
| Raw Fields | `ebitda`, `revenue`, `end_date` |
| Origin Source (Input) | Alpha Vantage |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Quarterly |
| History | ≥ 5 years |
| Calculation Logic | EBITDA Margin = `enterprise_ebitda` / `enterprise_revenue` |

### Missing / Error Tolerance & Quality Rules
- **Negative Revenue:** If `enterprise_revenue` ≤ 0, **DROP** the observation (margins on zero/negative revenue are mathematically meaningless).
- **Missing Values:** If either `enterprise_ebitda` or `enterprise_revenue` is NULL/NaN, **DROP** the observation. Do not attempt to impute EBITDA.
- **Soft Stale Warning:** If data age is in `(270, 365]` days, keep the observation but log `flag_financial_stale=True`.
- **Hard Expiration:** If data age is `> 365` days, **DROP** the observation and log `flag_data_expired=True`.

---

## 3. Debt/Equity Ratio (Financial Health Factor)

| Field | Specification |
|------|--------------|
| Metric Name | Debt/Equity |
| Raw Fields | `total_debt`, `total_shareholder_equity` |
| Origin Source (Input) | Alpha Vantage |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Financial update cadence: Quarterly; factor output cadence: Daily as-of (for backtest alignment) |
| History | ≥ 5 years |
| Calculation Logic | Debt/Equity = `total_debt` / `total_shareholder_equity` |

### Missing / Error Tolerance & Quality Rules
- **Missing Debt Fallback:** If `Total Debt` is missing directly from the API, attempt to calculate it as `Short-term Debt + Long-term Debt`. If both are missing, **DROP** the observation.
- **Negative Equity:** If `total_shareholder_equity` ≤ 0, **DROP** the observation. Highly distressed companies with negative equity produce misleading D/E ratios.
- **Soft Stale Warning:** If either component age is in `(270, 365]` days, keep the observation but log `flag_financial_stale=True`.
- **Hard Expiration:** If either component age is `> 365` days, **DROP** the observation and log `flag_data_expired=True`.
- **Interpolation:** Strict **NO**. Financial atomics remain quarterly updates; daily D/E is stepwise as-of alignment only (for backtest timeline consistency).

---

## 4. Price-to-Book Ratio (P/B) (Valuation Factor)

| Field | Specification |
|------|--------------|
| Metric Name | P/B Ratio |
| Raw Fields | Adjusted Close Price, `shares_outstanding`, `total_shareholder_equity` |
| Origin Source (Input) | Source A atomic factors (Alpha Vantage primary, yfinance fallback) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Monthly |
| History | ≥ 5 years |
| Calculation Logic | P/B = (Adjusted Close Price * `shares_outstanding`) / `total_shareholder_equity` |

### Missing / Error Tolerance & Quality Rules
- **Look-ahead Bias Prevention:** Price must strictly utilize the [-3 to 0 trading days] backward-looking rule.
- **Negative Equity:** If `total_shareholder_equity` ≤ 0, **DROP** the observation.
- **Missing Shares:** If `shares_outstanding` is missing, NaN, or ≤ 0, **DROP** the observation (market cap cannot be calculated).
- **Missing Price Tolerance:** If `Adjusted Close Price` is missing, NaN, or ≤ 0 after the 3-trading-day backward look, **DROP** the observation for that specific date.
- **Quality Auditing:** Log `flag_stale_price=True` warning when fallback price is older than 1 trading day.
- **Soft Stale Warning:** If financial components (`total_shareholder_equity`, `shares_outstanding`) age is in `(270, 365]` days, keep the observation but log `flag_financial_stale=True`.
- **Hard Expiration:** If financial components age is `> 365` days, **DROP** the observation and log `flag_data_expired=True`.
- **Logging Mode:** Default mode emits per-run summary counts (`stale_count`, `expired_count`) to avoid log flooding; set `QUALITY_VERBOSE_EVENTS=1` to emit per-event warning lines.
- **Extreme Values Cap:** Apply monthly cross-sectional 99th-percentile cap for P/B ratios. If the monthly cross section has fewer than `50` symbols, fallback to fixed cap `100.0` to avoid unstable small-sample quantiles.

---

## 5. News Sentiment Score (Alternative Risk Factor)

| Field | Specification |
|------|--------------|
| Metric Name | News Sentiment |
| Raw Fields | Article `title`, `summary`, `time_published` |
| Origin Source (Input) | External API (Alpha Vantage `NEWS_SENTIMENT`) |
| Target Storage (Output) | MinIO (Raw JSON) → PostgreSQL (`factor_observations`) |
| Frequency | Daily |
| History | ≥ 5 years (where available depending on API limits) |
| Calculation Logic | Article-level custom score from text (`title+summary`) → daily mean by `symbol+date` → fill missing days with `0.0` → rolling `30D` mean (`sentiment_30d_avg`). |

### Missing / Error Tolerance & Quality Rules
- **Raw Row Required Fields:** At transform stage, drop raw sentiment rows if required fields are missing/unparseable (`symbol`, `observation_date`, sentiment value). Do not impute malformed raw rows.
- **Zero News Fallback:** If NO news articles are found for a given company within the trailing 30-day window, **DO NOT DROP** the observation. Assign a neutral sentiment score of **0.0**.
- **No-News Day Handling:** For daily aggregation calendar, if a company has no article on a day, fill daily sentiment and article count with `0.0` before rolling `30D` computation.
- **Data Capping:** Hard cap all computed sentiment scores to a range of `[-1.0, 1.0]`.
- **Audit Logging:** Track article-volume context in transform/audit logs. `article_count_30d` is persisted daily in `factor_observations` by transform stage.

### Implementation Notes (Current Codebase)
- `extractor_b` stores raw news payloads in MinIO as JSONL monthly objects (`symbol x month`, deduplicated by URL with `title+time_published` fallback) and emits alternative atomic rows (`factor_name in {news_sentiment_daily, news_article_count_daily}`).
- Final daily signals are produced in transform stage (`modules/transform/factors.py`) as `factor_name in {sentiment_30d_avg, article_count_30d}`.
- The 30-day signal is time-window based (`rolling('30D')`), not row-count based.

---

## 6. Daily Return (Market Atomic)

| Field | Specification |
|------|--------------|
| Metric Name | Daily Return |
| Raw Fields | Adjusted Close Price (`P_t`, `P_{t-1}`) |
| Origin Source (Input) | Source A price history (Alpha Vantage primary, yfinance fallback) |
| Target Storage (Output) | PostgreSQL (`systematic_equity.factor_observations`) |
| Frequency | Daily |
| History | ≥ 5 years |
| Calculation Logic | `daily_return = ln(P_t / P_{t-1})` |

### Missing / Error Tolerance & Quality Rules
- **Insufficient History:** If no valid previous close exists (`P_{t-1}`), set `daily_return = NULL` for that day (do not fabricate returns).
- **Non-Positive Price Guard:** If either `P_t` or `P_{t-1}` is missing, NaN, or ≤ 0, set `daily_return = NULL`.
- **No Look-Ahead:** Strictly backward-looking (`t` uses only `t-1`), never future prices.
- **Market-Year Convention:** Use `252` trading days as the 1-year market convention for market-data staleness and annualized calculations.

---

# System-Level Acceptance Criteria (Definition of Done)

The pipeline and infrastructure must pass the following verifiable automated criteria before pull requests can be merged.

### 1. Data Coverage & Integrity Tests (`pytest`)
- **Historical Depth:** Pipeline must successfully backfill and persist ≥ 5 years of data for at least 3 test companies without throwing unhandled exceptions.
- **Missing Data Enforcement:** Unit tests must inject mocked stale data (e.g., Book Value > 12 months old) and explicitly assert that the ETL pipeline drops the observation.
- **Test Coverage Red Line:** The `pytest` suite running over the `transform` and `quality` modules must achieve a minimum of **80% code coverage**.

### 2. Query Capability & Indexing
- **EAV / Long Table Pattern:** The `factor_observations` schema must be designed as a "long table" (e.g., `symbol`, `observation_date`, `factor_name`, `factor_value`) rather than a wide table, satisfying the requirement that *adding a new metric must not require a schema ALTER operation*.
- **Performance:** B-Tree indexes must be applied to `symbol` and `observation_date`. The database must support sub-second query execution times for:
  1. Retrieving all metrics for a single `symbol` over a 5-year period.
  2. Retrieving a specific `factor_name` across all companies for a given calendar year.

### 3. Pipeline Robustness & Fault Tolerance
- **Dynamic Universe:** The pipeline must dynamically query `systematic_equity.company_static` at runtime. Adding or removing a symbol from this table must immediately reflect in the pipeline's execution loop without requiring codebase changes.
- **Idempotency & Uniqueness:** The pipeline must be idempotent. Rerunning the pipeline for the same date range must not duplicate data. PostgreSQL must utilize a composite Unique Constraint (`symbol`, `factor_name`, `observation_date`) combined with an `INSERT ... ON CONFLICT DO UPDATE` (Upsert) strategy.
- **Non-Blocking Execution:** If the API request for `company A` fails (e.g., HTTP 404 or 500), the pipeline must catch the exception, log the error trace to a `pipeline_runs` audit table, and seamlessly continue processing `company B`.
  - Current implementation: primary audit sink is PostgreSQL table `systematic_equity.pipeline_runs`; local JSONL remains as secondary debug mirror.

### 4. Quality Auditability
- **Lineage Tracing:** Every row in the curated PostgreSQL table must include a `run_id` or `updated_at` timestamp linking it back to the specific execution batch that fetched the raw data from MinIO.

