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
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "total_shareholder_equity",
            "factor_value": 1000.0,
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "book_value",
            "factor_value": 1000.0,
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "total_debt",
            "factor_value": 300.0,
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "enterprise_ebitda",
            "factor_value": 200.0,
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "enterprise_revenue",
            "factor_value": 1000.0,
            "source_report_date": "2026-03-31",
        },
    ]
    out = factors.compute_final_factor_records(atomic, run_date="2026-03-31", backfill_years=1)
    names = {r["factor_name"] for r in out}
    assert "pb_ratio" in names
    assert "debt_to_equity" in names
    assert "ebitda_margin" in names


def test_debt_to_equity_is_daily_asof_aligned():
    atomic = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-10",
            "factor_name": "total_debt",
            "factor_value": 300.0,
            "source_report_date": "2026-01-10",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2026-01-10",
            "factor_name": "total_shareholder_equity",
            "factor_value": 100.0,
            "source_report_date": "2026-01-10",
        },
    ]
    out = factors.compute_final_factor_records(atomic, run_date="2026-01-15", backfill_years=1)
    dte = [r for r in out if r["factor_name"] == "debt_to_equity"]
    assert len(dte) == 6  # 2026-01-10 ... 2026-01-15
    assert all(r["metric_frequency"] == "daily" for r in dte)
    assert {r["factor_value"] for r in dte} == {3.0}
    assert {r["source_report_date"] for r in dte} == {"2026-01-10"}


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
    assert len(s) > 100
    assert len(c) > 100
    assert all(r["metric_frequency"] == "daily" for r in s)
    assert all(r["metric_frequency"] == "daily" for r in c)

    by_date = {r["observation_date"]: r for r in s}
    count_by_date = {r["observation_date"]: r for r in c}
    assert "2026-01-31" in by_date and "2026-01-31" in count_by_date
    assert "2026-02-28" in by_date and "2026-02-28" in count_by_date
    # Jan-31 includes two positive sentiment days in trailing 30D.
    assert abs(by_date["2026-01-31"]["factor_value"] - 0.02) < 1e-12
    assert count_by_date["2026-01-31"]["factor_value"] == 2.0
    # Feb-28 has no news in trailing 30D window -> zero fallback remains effective.
    assert by_date["2026-02-28"]["factor_value"] == 0.0
    assert count_by_date["2026-02-28"]["factor_value"] == 0.0


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


def test_compute_final_factor_records_pb_ratio_uses_dynamic_q99_for_large_monthly_cross_section():
    atomic = []
    obs_date = "2026-03-31"
    for i in range(50):
        symbol = f"S{i:03d}"
        price = 1.0 if i < 49 else 1000.0
        atomic.extend(
            [
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "adjusted_close_price",
                    "factor_value": price,
                },
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "shares_outstanding",
                    "factor_value": 100.0,
                    "source_report_date": obs_date,
                },
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "total_shareholder_equity",
                    "factor_value": 100.0,
                    "source_report_date": obs_date,
                },
            ]
        )

    out = factors.compute_final_factor_records(atomic, run_date=obs_date, backfill_years=1)
    pb_rows = [r for r in out if r["factor_name"] == "pb_ratio" and r["observation_date"] == obs_date]
    assert len(pb_rows) == 50
    outlier = [r for r in pb_rows if r["symbol"] == "S049"][0]
    # Dynamic q99 should cap the outlier below its raw value (1000),
    # and not use the small-sample fallback cap(=100).
    assert outlier["factor_value"] < 1000.0
    assert outlier["factor_value"] > 100.0


def test_compute_final_factor_records_pb_ratio_falls_back_to_100_cap_for_small_cross_section():
    atomic = []
    obs_date = "2026-03-31"
    for i in range(10):
        symbol = f"T{i:03d}"
        price = 1.0 if i < 9 else 1000.0
        atomic.extend(
            [
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "adjusted_close_price",
                    "factor_value": price,
                },
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "shares_outstanding",
                    "factor_value": 100.0,
                    "source_report_date": obs_date,
                },
                {
                    "symbol": symbol,
                    "observation_date": obs_date,
                    "factor_name": "total_shareholder_equity",
                    "factor_value": 100.0,
                    "source_report_date": obs_date,
                },
            ]
        )

    out = factors.compute_final_factor_records(atomic, run_date=obs_date, backfill_years=1)
    pb_rows = [r for r in out if r["factor_name"] == "pb_ratio" and r["observation_date"] == obs_date]
    assert len(pb_rows) == 10
    outlier = [r for r in pb_rows if r["symbol"] == "T009"][0]
    assert outlier["factor_value"] == 100.0


def test_financial_staleness_logs_soft_and_hard_events(caplog):
    atomic = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "adjusted_close_price",
            "factor_value": 50.0,
        },
        # stale but still usable for 2026-12-31 (age 275 days)
        {
            "symbol": "AAPL",
            "observation_date": "2026-03-31",
            "factor_name": "shares_outstanding",
            "factor_value": 100.0,
            "source_report_date": "2026-03-31",
        },
        # expired for 2026-12-31 (age 366 days)
        {
            "symbol": "AAPL",
            "observation_date": "2025-12-30",
            "factor_name": "total_shareholder_equity",
            "factor_value": 1000.0,
            "source_report_date": "2025-12-30",
        },
    ]

    with caplog.at_level("WARNING"):
        out = factors.compute_final_factor_records(atomic, run_date="2026-12-31", backfill_years=1)

    # total_shareholder_equity expired => pb_ratio should be dropped for this date.
    pb_rows = [r for r in out if r["factor_name"] == "pb_ratio" and r["observation_date"] == "2026-12-31"]
    assert pb_rows == []

    joined = "\n".join(caplog.messages)
    assert "quality_event_summary" in joined
    assert "stale_count=" in joined
    assert "expired_count=" in joined
    assert "stale_by_factor={'pb_ratio':" in joined
    assert "expired_by_factor={'pb_ratio':" in joined


def test_financial_staleness_verbose_event_logging(monkeypatch, caplog):
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
            "source_report_date": "2026-03-31",
        },
        {
            "symbol": "AAPL",
            "observation_date": "2025-12-30",
            "factor_name": "total_shareholder_equity",
            "factor_value": 1000.0,
            "source_report_date": "2025-12-30",
        },
    ]
    monkeypatch.setenv("QUALITY_VERBOSE_EVENTS", "1")
    with caplog.at_level("WARNING"):
        factors.compute_final_factor_records(atomic, run_date="2026-12-31", backfill_years=1)
    joined = "\n".join(caplog.messages)
    assert "flag_financial_stale=True" in joined
    assert "flag_data_expired=True" in joined
