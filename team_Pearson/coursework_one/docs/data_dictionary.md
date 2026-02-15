# Data Dictionary

> Descriptions for each core table and field, including data type, unit, source, and notes. Some fields can be updated after code development.

---

## 1. Table: company_static

| Column Name | Type | Description | Unit | Notes |
|-------------|------|-------------|------|------|
| symbol | TEXT | Stock symbol | N/A | Primary key, used to link to other tables |
| company_name | TEXT | Company name | N/A | - |
| sector | TEXT | Industry sector | N/A | - |
| market_cap | FLOAT | Market capitalization | USD | Latest market cap, may change over time |

---

## 2. Table: factor_observations

| Column Name | Type | Description | Unit | Notes |
|-------------|------|-------------|------|------|
| symbol | TEXT | Stock symbol | N/A | Links to company_static.symbol |
| observation_date | DATE | Factor observation date | YYYY-MM-DD | - |
| factor_name | TEXT | Factor name | N/A | Dividend Yield, EBITDA Margin, Debt/Equity, P/B, Sentiment |
| factor_value | FLOAT | Factor value | Ratio / Score | Dividend Yield / EBITDA Margin / Debt-Equity / P/B / Sentiment (-1~1) |
| run_date | DATE | ETL execution date | YYYY-MM-DD | Tracks the batch of execution |
| updated_at | TIMESTAMP | Last update timestamp | ISO 8601 | Optional, for data versioning |
| flag_stale_price | BOOLEAN | Stale price flag | True/False | Specific to Dividend Yield, for quality audit |
| article_count_30d | INTEGER | Number of news articles in past 30 days | Count | Specific to Sentiment factor, distinguish 0.0 from no news vs mixed news |
| Data_Expired | BOOLEAN | Data expired flag | True/False | Specific to EBITDA Margin, Debt/Equity, P/B, for quality audit |

---

## 3. Table: pipeline_runs (Audit Table)

| Column Name | Type | Description | Unit | Notes |
|-------------|------|-------------|------|------|
| run_id | UUID / TEXT | Unique ETL batch identifier | N/A | Each pipeline run generates a unique ID |
| start_time | TIMESTAMP | Start time of run | ISO 8601 | - |
| end_time | TIMESTAMP | End time of run | ISO 8601 | - |
| status | TEXT | Run status | SUCCESS / FAIL | - |
| error_message | TEXT | Error message | N/A | Only filled when status=FAIL |
| company_symbol | TEXT | Company being processed | N/A | Optional, for tracking errors per company |
