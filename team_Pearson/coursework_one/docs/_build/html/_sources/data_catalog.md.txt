# Data Catalog

> This document lists all core datasets used in the coursework project, including source, type, storage location, and description, to facilitate understanding and usage by team members.

| Dataset Name | Type | Storage | Description | Owner / Role |
|--------------|------|---------|------------|--------------|
| company_static | Structured Table | PostgreSQL (systematic_equity.company_static) | Investable universe master table, contains symbol, name, sector, market cap, etc. | Role 5 |
| raw_price_data | JSON / CSV | MinIO | Daily stock price and dividend data from external API (yfinance) | Role 6 |
| raw_financials | Structured | PostgreSQL (internal tables) | Enterprise financial data (EBITDA, Revenue, Book Value, Debt, etc.) | Role 6 / 8 |
| raw_news_sentiment | JSON | MinIO | Raw news text and sentiment scores from news APIs (Alpha Vantage / NewsAPI) | Role 7 |
| factor_observations | Structured / Long Table | PostgreSQL (systematic_equity.factor_observations) | Final calculated factor values (Dividend Yield, EBITDA Margin, Debt/Equity, P/B, Sentiment) | Role 8 |
| pipeline_runs | Structured | PostgreSQL (audit table) | Records ETL execution metadata including run_id, start/end time, status, error info | Role 8 |
| TBD | Structured / Raw | TBD | Other auxiliary or temporary datasets, to be updated after development | TBD |
