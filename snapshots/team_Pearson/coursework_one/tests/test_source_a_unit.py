import importlib
import json

import pandas as pd

source_a = importlib.import_module("modules.input.extract_source_a")


class _FakeTickerWithDebt:
    def __init__(self):
        self.quarterly_balance_sheet = pd.DataFrame({"2025Q4": [123.0]}, index=["Total Debt"])


class _FakeTickerNoDebt:
    def __init__(self):
        self.quarterly_balance_sheet = pd.DataFrame()


def test_extract_source_a_test_mode(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    out = source_a.extract_source_a(
        symbols=["AAPL", "MSFT"],
        run_date="2026-02-14",
        backfill_years=1,
        frequency="daily",
    )
    assert len(out) == 2
    assert all(r["source"] == "source_a_test" for r in out)


def test_extract_total_debt_found():
    assert source_a._extract_total_debt(_FakeTickerWithDebt()) == 123.0


def test_extract_total_debt_missing_returns_none():
    assert source_a._extract_total_debt(_FakeTickerNoDebt()) is None


def test_build_records_from_history_shape():
    idx = pd.to_datetime(["2026-02-13", "2026-02-14"])
    history = pd.DataFrame(
        {
            "Close": [100.0, 101.0],
            "Dividends": [0.0, 0.1],
        },
        index=idx,
    )
    out = source_a._build_records_from_history(
        symbol="AAPL",
        history=history,
        run_date="2026-02-14",
        frequency="daily",
        total_debt=500.0,
    )
    assert len(out) == 5
    names = {r["factor_name"] for r in out}
    assert {"adjusted_close_price", "dividend_per_share", "total_debt"}.issubset(names)


def test_extract_source_a_handles_symbol_failure(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)

    def _boom(symbol, years_back, max_retries=3):
        raise RuntimeError("boom")

    monkeypatch.setattr(source_a, "_download_price_history", _boom)
    monkeypatch.setattr(source_a, "_save_raw_to_minio", lambda *args, **kwargs: None)

    out = source_a.extract_source_a(
        symbols=["AAPL"],
        run_date="2026-02-14",
        backfill_years=1,
        frequency="daily",
        config={"minio": {}},
    )
    assert out == []


def test_load_config_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "missing.yaml"
    assert source_a.load_config(str(missing)) == {}


def test_load_config_reads_yaml(tmp_path):
    cfg = tmp_path / "conf.yaml"
    cfg.write_text("pipeline:\n  company_limit: 2\n", encoding="utf-8")
    out = source_a.load_config(str(cfg))
    assert out["pipeline"]["company_limit"] == 2


def test_save_raw_to_minio_skips_when_config_incomplete():
    source_a._save_raw_to_minio(config={}, symbol="AAPL", run_date="2026-02-14", payload={})


def test_save_raw_to_minio_happy_path(monkeypatch):
    events = {"put": None}

    class _FakeMinio:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def bucket_exists(self, bucket):
            return True

        def make_bucket(self, bucket):
            raise AssertionError("should not create bucket when exists")

        def put_object(self, bucket, object_name, data, length, content_type):
            events["put"] = (bucket, object_name, length, content_type, json.loads(data.read()))

    monkeypatch.setitem(__import__("sys").modules, "minio", type("M", (), {"Minio": _FakeMinio}))
    cfg = {
        "minio": {
            "endpoint": "localhost:9000",
            "access_key": "x",
            "secret_key": "y",
            "bucket": "csreport",
            "secure": False,
        }
    }
    source_a._save_raw_to_minio(cfg, "AAPL", "2026-02-14", {"k": "v"})
    assert events["put"][0] == "csreport"
    assert "raw/source_a/pricing_fundamentals/" in events["put"][1]


def test_save_raw_to_minio_serializes_timestamp(monkeypatch):
    events = {"payload": None}

    class _FakeMinio:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def bucket_exists(self, bucket):
            return True

        def make_bucket(self, bucket):
            raise AssertionError("should not create bucket when exists")

        def put_object(self, bucket, object_name, data, length, content_type):
            _ = (bucket, object_name, length, content_type)
            events["payload"] = json.loads(data.read())

    monkeypatch.setitem(__import__("sys").modules, "minio", type("M", (), {"Minio": _FakeMinio}))
    cfg = {
        "minio": {
            "endpoint": "localhost:9000",
            "access_key": "x",
            "secret_key": "y",
            "bucket": "csreport",
            "secure": False,
        }
    }
    payload = {"history": [{"Date": pd.Timestamp("2026-02-14"), "Close": 101.0}]}
    source_a._save_raw_to_minio(cfg, "AAPL", "2026-02-14", payload)
    assert events["payload"]["history"][0]["Date"].startswith("2026-02-14")


def test_download_price_history_with_fake_yfinance(monkeypatch):
    class _FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, period, auto_adjust=False):
            idx = pd.to_datetime(["2026-02-13"])
            return pd.DataFrame({"Close": [101.0], "Dividends": [0.0]}, index=idx)

    monkeypatch.setitem(
        __import__("sys").modules, "yfinance", type("YF", (), {"Ticker": _FakeTicker})
    )
    ticker, history = source_a._download_price_history("AAPL", 1)
    assert ticker.symbol == "AAPL"
    assert len(history) == 1


def test_build_technical_records_drops_if_less_than_20_days():
    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    history = pd.DataFrame({"Close": [float(100 + i) for i in range(10)]}, index=idx)
    out = source_a._build_technical_records("AAPL", history, "daily", "alpha_vantage")
    assert out == []


def test_build_technical_records_generates_momentum_and_volatility():
    idx = pd.date_range("2026-01-01", periods=25, freq="D")
    history = pd.DataFrame({"Close": [float(100 + i) for i in range(25)]}, index=idx)
    out = source_a._build_technical_records("AAPL", history, "daily", "alpha_vantage")
    names = {r["factor_name"] for r in out}
    assert "momentum_1m" in names
    assert "volatility_20d" in names
    assert all(r["source"] == "alpha_vantage" for r in out)


def test_build_technical_records_drops_non_positive_prices():
    idx = pd.date_range("2026-01-01", periods=25, freq="D")
    prices = [float(100 + i) for i in range(25)]
    prices[20] = 0.0
    history = pd.DataFrame({"Close": prices}, index=idx)

    out = source_a._build_technical_records("AAPL", history, "daily", "alpha_vantage")
    bad_date = idx[20].date().isoformat()
    assert all(r["observation_date"] != bad_date for r in out)
    assert all(pd.notna(r["value"]) for r in out)


def test_download_with_provider_falls_back_to_yfinance(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "x")

    def _boom(*args, **kwargs):
        raise RuntimeError("alpha down")

    class _Ticker:
        symbol = "AAPL"

    def _ok(symbol, years_back, max_retries=3):
        _ = (symbol, years_back, max_retries)
        idx = pd.to_datetime(["2026-02-13"])
        return _Ticker(), pd.DataFrame({"Close": [101.0], "Dividends": [0.0]}, index=idx)

    monkeypatch.setattr(source_a, "_download_price_history_alpha_vantage", _boom)
    monkeypatch.setattr(source_a, "_download_price_history", _ok)

    source, ticker, history = source_a._download_with_provider(
        "AAPL",
        1,
        {"source_a": {"primary_source": "alpha_vantage", "enable_yfinance_fallback": True}},
    )
    assert source == "yfinance"
    assert ticker.symbol == "AAPL"
    assert len(history) == 1


def test_resolve_alpha_key_from_config_when_env_missing(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_KEY", raising=False)
    key = source_a._resolve_alpha_key({"api": {"alpha_vantage_key": "abc123"}})
    assert key == "abc123"


def test_select_source_order_default_and_with_fallback_disabled():
    assert source_a._select_source_order({}) == ["alpha_vantage", "yfinance"]
    out = source_a._select_source_order(
        {"source_a": {"primary_source": "alpha_vantage", "enable_yfinance_fallback": False}}
    )
    assert out == ["alpha_vantage"]


def test_history_from_payload_uses_observation_date():
    payload = {
        "history": [
            {"observation_date": "2026-02-13", "Close": 100.0, "Dividends": 0.0},
            {"observation_date": "2026-02-14", "Close": 101.0, "Dividends": 0.1},
        ]
    }
    history = source_a._history_from_payload(payload)
    assert len(history) == 2
    assert "Close" in history.columns


def test_load_raw_from_minio_returns_none_when_config_incomplete():
    out = source_a._load_raw_from_minio({}, "AAPL", "2026-02-14")
    assert out is None


def test_download_with_provider_uses_alpha_vantage_first(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "x")

    def _alpha_ok(symbol, years_back, api_key, timeout_seconds=30):
        _ = (symbol, years_back, api_key, timeout_seconds)
        idx = pd.to_datetime(["2026-02-13", "2026-02-14"])
        history = pd.DataFrame({"Close": [100.0, 101.0], "Dividends": [0.0, 0.1]}, index=idx)
        return None, history

    monkeypatch.setattr(source_a, "_download_price_history_alpha_vantage", _alpha_ok)

    source, ticker, history = source_a._download_with_provider(
        "AAPL",
        1,
        {"source_a": {"primary_source": "alpha_vantage", "enable_yfinance_fallback": True}},
    )
    assert source == "alpha_vantage"
    assert ticker is None
    assert len(history) == 2
