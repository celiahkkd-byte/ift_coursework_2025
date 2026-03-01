from modules.output.normalize import normalize_records


def test_normalize_from_alternative_keys_and_type_cast():
    raw = [{"symbol": "SYM00001", "date": "2026-02-14T12:00:00Z", "metric": "pb", "value": "1.2"}]
    out = normalize_records(raw)

    assert len(out) == 1
    assert out[0]["symbol"] == "SYM00001"
    assert out[0]["observation_date"] == "2026-02-14"
    assert out[0]["factor_name"] == "pb"
    assert out[0]["factor_value"] == 1.2
    assert out[0]["source"] == "unknown"
    assert out[0]["metric_frequency"] == "unknown"


def test_normalize_prefers_explicit_factor_value():
    raw = [
        {
            "symbol": "SYM00002",
            "observation_date": "2026-02-14",
            "factor_name": "de_ratio",
            "factor_value": 3.0,
            "value": 99.0,
            "source": "source_a",
            "metric_frequency": "DAILY",
        }
    ]
    out = normalize_records(raw)
    assert out[0]["observation_date"] == "2026-02-14"
    assert out[0]["factor_value"] == 3.0
    assert out[0]["source"] == "source_a"
    assert out[0]["metric_frequency"] == "daily"


def test_normalize_empty_or_nan_values_become_none():
    raw = [
        {
            "symbol": "SYM00003",
            "observation_date": "2026-02-14",
            "factor_name": "x",
            "factor_value": "NaN",
        },
        {"symbol": "SYM00004", "observation_date": "2026-02-14", "factor_name": "y", "value": ""},
    ]
    out = normalize_records(raw)
    assert out[0]["factor_value"] is None
    assert out[1]["factor_value"] is None


def test_normalize_drops_invalid_observation_date():
    raw = [
        {"symbol": "SYM1", "observation_date": "2026-02-14", "factor_name": "x", "value": 1.0},
        {"symbol": "SYM2", "observation_date": "NaT", "factor_name": "y", "value": 2.0},
        {"symbol": "SYM3", "observation_date": "", "factor_name": "z", "value": 3.0},
    ]
    out = normalize_records(raw)
    assert len(out) == 1
    assert out[0]["symbol"] == "SYM1"
