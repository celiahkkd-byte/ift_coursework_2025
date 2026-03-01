from modules.output.quality import run_quality_checks


def test_quality_counts_missing_and_duplicates_by_db_unique_key():
    rows = [
        {
            "symbol": "SYM00001",
            "observation_date": "2026-02-14",
            "factor_name": "pb_ratio",
            "factor_value": 1.0,
            "source": "source_a",
            "metric_frequency": "daily",
        },
        # Same (symbol, factor_name, observation_date) => duplicate in DB sense
        {
            "symbol": "SYM00001",
            "observation_date": "2026-02-14",
            "factor_name": "pb_ratio",
            "factor_value": None,
            "source": "source_b",
            "metric_frequency": "daily",
        },
    ]

    report = run_quality_checks(rows)
    assert report["row_count"] == 2
    assert report["missing_values"] == 1
    assert report["duplicates"] == 1
    assert report["missing_required"] == 0
    assert report["invalid_frequency"] == 0


def test_quality_flags_missing_required_and_invalid_frequency():
    rows = [
        {
            "symbol": None,
            "observation_date": "2026-02-14",
            "factor_name": "pb_ratio",
            "factor_value": 1.0,
            "source": "source_a",
            "metric_frequency": "daily",
        },
        {
            "symbol": "SYM00002",
            "observation_date": "2026-02-14",
            "factor_name": "pb_ratio",
            "factor_value": 1.0,
            "source": "source_a",
            "metric_frequency": "hourly",  # invalid
        },
    ]
    report = run_quality_checks(rows)
    assert report["missing_required"] == 1
    assert report["invalid_frequency"] == 1
    assert report["passed"] is False
