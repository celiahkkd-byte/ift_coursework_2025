from modules.input.extract_source_b import (
    extract_source_b,
    ingest_source_b_raw,
    transform_source_b_features,
)


def test_ingest_source_b_raw_stub_returns_empty():
    out = ingest_source_b_raw(["AAPL"], "2026-02-14", 1, "daily", config={})
    assert out == []


def test_transform_source_b_features_default_empty(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)
    out = transform_source_b_features([], ["AAPL"], "2026-02-14", "daily")
    assert out == []


def test_extract_source_b_test_mode(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    out = extract_source_b(["AAPL", "MSFT"], "2026-02-14", 1, "daily", config={})
    assert len(out) == 2
    assert all(r["source"] == "extractor_b" for r in out)
