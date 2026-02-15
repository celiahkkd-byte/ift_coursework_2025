from modules.output.quality import run_quality_checks


def test_quality_counts_missing_and_duplicates():
    rows = [
        {
            "company_id": "C00001",
            "observation_date": "2026-02-14",
            "factor_name": "pb",
            "factor_value": 1.0,
            "source": "source_a",
        },
        {
            "company_id": "C00001",
            "observation_date": "2026-02-14",
            "factor_name": "pb",
            "factor_value": None,
            "source": "source_a",
        },
    ]

    report = run_quality_checks(rows)
    assert report["row_count"] == 2
    assert report["missing_values"] == 1
    assert report["duplicates"] == 1
