from __future__ import annotations

from modules.transform import factors


def test_compute_final_factor_records_dividend_yield_monthly():
    atomic = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-30",
            "factor_name": "adjusted_close_price",
            "factor_value": 100.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2025-12-15",
            "factor_name": "dividend_per_share",
            "factor_value": 1.2,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2025-09-15",
            "factor_name": "dividend_per_share",
            "factor_value": 0.8,
        },
    ]
    out = factors.compute_final_factor_records(atomic, run_date="2026-01-31", backfill_years=1)
    dy = [r for r in out if r["factor_name"] == "dividend_yield"]
    assert len(dy) == 1
    assert dy[0]["observation_date"] == "2026-01-31"
    assert abs(dy[0]["factor_value"] - 0.02) < 1e-9


def test_compute_final_factor_records_pb_de_ebitda():
    atomic = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "adjusted_close_price",
            "factor_value": 50.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "shares_outstanding",
            "factor_value": 100.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "book_value",
            "factor_value": 1000.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "total_debt",
            "factor_value": 300.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "enterprise_ebitda",
            "factor_value": 200.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "enterprise_revenue",
            "factor_value": 1000.0,
        },
    ]
    out = factors.compute_final_factor_records(atomic, run_date="2026-03-31", backfill_years=1)
    names = {r["factor_name"] for r in out}
    assert "pb_ratio" in names
    assert "debt_to_equity" in names
    assert "ebitda_margin" in names


def test_compute_final_factor_records_sentiment_with_zero_news_fallback():
    atomic = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-15",
            "factor_name": "news_sentiment_daily",
            "factor_value": 0.5,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-16",
            "factor_name": "news_sentiment_daily",
            "factor_value": 0.1,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-15",
            "factor_name": "news_article_count_daily",
            "factor_value": 1.0,
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-16",
            "factor_name": "news_article_count_daily",
            "factor_value": 1.0,
        },
    ]
    out = factors.compute_final_factor_records(atomic, run_date="2026-02-28", backfill_years=1)
    s = [r for r in out if r["factor_name"] == "sentiment_30d_avg"]
    c = [r for r in out if r["factor_name"] == "article_count_30d"]
    assert len(s) >= 2
    assert len(c) >= 2
    by_date = {r["observation_date"]: r["factor_value"] for r in s}
    count_by_date = {r["observation_date"]: r["factor_value"] for r in c}
    assert "2026-01-31" in by_date
    assert "2026-02-28" in by_date
    assert by_date["2026-02-28"] == 0.0
    assert "2026-01-31" in count_by_date
    assert "2026-02-28" in count_by_date
    assert count_by_date["2026-01-31"] == 2.0
    assert count_by_date["2026-02-28"] == 0.0


def test_build_and_load_final_factors_calls_loader(monkeypatch):
    monkeypatch.setattr(
        factors,
        "_load_atomic_records_from_postgres",
        lambda **kwargs: [
            {
                "symbol": "AAPL",
                "observation_date": "2026-01-30",
                "factor_name": "adjusted_close_price",
                "factor_value": 100.0,
            },
            {
                "symbol": "AAPL",
                "observation_date": "2025-12-15",
                "factor_name": "dividend_per_share",
                "factor_value": 1.0,
            },
        ],
    )

    captured = {}

    def _fake_load(rows, dry_run=False, table_name="factor_observations"):
        captured["rows"] = rows
        captured["dry_run"] = dry_run
        captured["table_name"] = table_name
        return len(rows)

    monkeypatch.setattr(factors, "load_curated", _fake_load)

    out = factors.build_and_load_final_factors(
        run_date="2026-01-31",
        backfill_years=1,
        symbols=["AAPL"],
        dry_run=True,
    )
    assert out >= 1
    assert captured["dry_run"] is True
    assert any(r["factor_name"] == "dividend_yield" for r in captured["rows"])
