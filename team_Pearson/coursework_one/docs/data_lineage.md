# Data Lineage

> Shows the flow of core factors from raw data sources to the final PostgreSQL table. A logical diagram can be placed at docs/images/architecture.png.

---

## 1. Logical Flow Diagram

![Architecture Diagram](images/architecture.png)

- External APIs / Internal PostgreSQL → MinIO → ETL → PostgreSQL
- Factor calculations → written to factor_observations
- Audit / pipeline_runs tracks ETL execution batches

---

## 2. Factor-Level Lineage

| Factor | Raw Source | Transformation / Calculation | Storage |
|--------|------------|------------------------------|---------|
| Dividend Yield | yfinance API: dividends, price | DY = Trailing 12-Month DPS / Adjusted Close Price | factor_observations |
| EBITDA Margin | PostgreSQL: enterprise_ebitda, revenue | EBITDA / Revenue | factor_observations |
| Debt/Equity | yfinance + internal DB | Total Debt / Book Value | factor_observations |
| P/B Ratio | yfinance price + internal outstanding_shares + book_value | Price * Shares / Book Value | factor_observations |
| Sentiment | News API raw JSON | 30-day rolling average of sentiment_score (-1 to 1) | factor_observations |

---

## 3. Transformation Notes

- **Raw Data → MinIO**: All API responses stored as raw JSON/CSV, retaining metadata (timestamp, source)
- **ETL Transformation**:  
  - Compute standardized factor values from raw_price_data, raw_financials, raw_news_sentiment  
  - Include missing value handling, forward-filling, capping extreme values, and quality flags
- **PostgreSQL factor_observations**: Long table structure, composite primary key (symbol + observation_date + factor_name) ensures uniqueness
- **pipeline_runs**: Tracks batch execution, supports audit and traceability
