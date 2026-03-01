# Usage Instructions

## Dry-run pipeline (default extractor: source_a)

```bash
cd /Users/celiawong/Desktop/ift_coursework_2025/team_Pearson/coursework_one
poetry run python Main.py --run-date 2026-02-14 --frequency daily --dry-run
```

## Override extractor list via CLI

```bash
poetry run python Main.py \
  --run-date 2026-02-14 \
  --frequency daily \
  --dry-run \
  --enabled-extractors source_a,source_b
```

## Full test run

```bash
poetry run pytest -q
```

## Coverage run

```bash
poetry run pytest --cov=modules --cov-report=term-missing -q
```

## Factor Dictionary (Source A)

| factor_name | raw fields | formula | window | drop rule | frequency | source priority |
| --- | --- | --- | --- | --- | --- | --- |
| momentum_1m | Adjusted Close Price | `(Price_t / Price_{t-20}) - 1` | 20 trading days | drop if history < 20 trading days or adjusted close <= 0 | daily | alpha_vantage -> yfinance |
| volatility_20d | Adjusted Close Price | `std(pct_change(price), rolling 20)` (simple return, non-annualized) | 20 trading days | drop if history < 20 trading days or adjusted close <= 0 | daily | alpha_vantage -> yfinance |

## Company Universe (Documentation Example Only)

Runtime company selection comes from PostgreSQL (`systematic_equity.company_static`).
The following is only a documentation example:

```yaml
companies:
  - AAPL
  - MSFT
  - GOOGL
  - AMZN
  - JPM
```
