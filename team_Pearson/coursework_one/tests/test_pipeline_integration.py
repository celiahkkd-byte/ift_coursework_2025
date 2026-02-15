import Main
from modules.output.normalize import normalize_records
from modules.output.quality import run_quality_checks


def test_collect_normalize_quality_chain():
    company_ids = ["C00001", "C00002"]
    raw = Main.collect_raw_records(company_ids, "2026-02-14", "daily", 5)
    assert len(raw) == 4  # source_a + source_b

    curated = normalize_records(raw)
    report = run_quality_checks(curated)

    assert report["row_count"] == len(curated)
    assert report["missing_values"] == 0
