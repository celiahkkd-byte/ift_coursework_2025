import Main
from modules.output.normalize import normalize_records
from modules.output.quality import run_quality_checks


def test_collect_normalize_quality_chain(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    symbols = ["SYM00001", "SYM00002"]

    raw = Main.collect_raw_records(symbols, "2026-02-14", "daily", 5)
    assert len(raw) > 0

    curated = normalize_records(raw)
    assert len(curated) == len(raw)

    report = run_quality_checks(curated)

    assert report["row_count"] == len(curated)
    assert "missing_values" in report
    assert "duplicates" in report
