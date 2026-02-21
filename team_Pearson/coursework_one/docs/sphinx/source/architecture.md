# Architecture Overview

## Objective
Provide a reusable PostgreSQL connectivity layer and dynamic investable universe extraction.

## Data Source
PostgreSQL table:
- `systematic_equity.company_static`

## Role 5 Components

### db_connection.py
- Reads credentials from environment variables
- Provides reusable `get_db_connection()`

### universe.py
- Provides `get_company_universe(company_limit=None)`
- Supports CLI usage with `--company-limit`
- Supports pipeline parameters (`--run-date`, `--frequency`)

## Data Flow
PostgreSQL → db_connection → universe extraction → downstream ETL modules