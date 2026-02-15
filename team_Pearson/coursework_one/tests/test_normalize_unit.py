from modules.output.normalize import normalize_records


def test_normalize_from_alternative_keys():
    raw = [{"symbol": "SYM00001", "date": "2026-02-14", "metric": "pb", "value": 1.2}]
    out = normalize_records(raw)
    assert len(out) == 1
    assert out[0]["symbol"] == "SYM00001"
    assert out[0]["observation_date"] == "2026-02-14"
    assert out[0]["factor_name"] == "pb"
    assert out[0]["factor_value"] == 1.2
    assert out[0]["source"] == "unknown"


def test_normalize_prefers_explicit_factor_value():
    raw = [
        {
            "symbol": "SYM00002",
            "observation_date": "2026-02-14",
            "factor_name": "de_ratio",
            "factor_value": 3.0,
            "value": 99.0,
            "source": "source_a",
        }
    ]
    out = normalize_records(raw)
    assert out[0]["observation_date"] == "2026-02-14"
    assert out[0]["factor_value"] == 3.0
    assert out[0]["source"] == "source_a"
