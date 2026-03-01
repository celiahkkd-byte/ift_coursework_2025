import pytest

import modules.output.load as load_mod
from modules.output.load import load_curated


def test_load_curated_empty_returns_zero():
    assert load_curated([], dry_run=False) == 0


def test_load_curated_dry_run_returns_record_count():
    rows = [
        {"symbol": "AAPL", "observation_date": "2026-02-14", "factor_name": "x", "value": 1.0},
        {"symbol": "MSFT", "observation_date": "2026-02-14", "factor_name": "x", "value": 2.0},
    ]
    assert load_curated(rows, dry_run=True) == 2


def test_load_curated_missing_required_raises_before_db():
    rows = [{"observation_date": "2026-02-14", "factor_name": "x", "value": 1.0}]
    with pytest.raises(ValueError, match="Missing required columns"):
        load_curated(rows, dry_run=False)


def test_load_curated_executes_upsert(monkeypatch):
    executed = {"called": False, "constraint": None}

    class _FakeConn:
        def execute(self, stmt):
            executed["called"] = True
            executed["stmt"] = stmt

    class _Ctx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def begin(self):
            return _Ctx()

    class _Excluded:
        factor_value = "fv"
        source = "src"
        metric_frequency = "mf"
        source_report_date = "srd"

    class _Stmt:
        excluded = _Excluded()

        def values(self, records):
            self.records = records
            return self

        def on_conflict_do_update(self, constraint, set_):
            executed["constraint"] = constraint
            executed["set_keys"] = sorted(set_.keys())
            return "UPSERT_STMT"

    monkeypatch.setattr(load_mod, "datetime", type("DT", (), {"now": staticmethod(lambda: "now")}))

    monkeypatch.setitem(__import__("sys").modules, "pandas", __import__("pandas"))

    import sqlalchemy
    import sqlalchemy.dialects.postgresql as pg

    class _Col:
        def __init__(self, name):
            self.name = name

    class _FakeTable:
        columns = [
            _Col("symbol"),
            _Col("observation_date"),
            _Col("factor_name"),
            _Col("factor_value"),
            _Col("source"),
            _Col("metric_frequency"),
            _Col("source_report_date"),
        ]

    monkeypatch.setattr(load_mod, "get_db_engine", lambda: _Engine())
    monkeypatch.setattr(sqlalchemy, "MetaData", lambda: object())
    monkeypatch.setattr(
        sqlalchemy,
        "Table",
        lambda *args, **kwargs: _FakeTable(),
    )
    monkeypatch.setattr(pg, "insert", lambda table: _Stmt())

    rows = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-02-14",
            "factor_name": "x",
            "value": 1.0,
            "source": "source_a",
            "frequency": "daily",
        }
    ]
    out = load_curated(rows, dry_run=False)
    assert out == 1
    assert executed["called"] is True
    assert executed["constraint"] == "uniq_observation"


def test_load_curated_ignores_extra_columns_not_in_table(monkeypatch):
    captured = {}

    class _FakeConn:
        def execute(self, stmt):
            captured["stmt"] = stmt

    class _Ctx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def begin(self):
            return _Ctx()

    class _Excluded:
        factor_value = "fv"
        source = "src"
        metric_frequency = "mf"
        source_report_date = "srd"

    class _Stmt:
        excluded = _Excluded()

        def values(self, records):
            captured["records"] = records
            return self

        def on_conflict_do_update(self, constraint, set_):
            return "UPSERT_STMT"

    class _Col:
        def __init__(self, name):
            self.name = name

    class _FakeTable:
        columns = [
            _Col("symbol"),
            _Col("observation_date"),
            _Col("factor_name"),
            _Col("factor_value"),
        ]

    monkeypatch.setitem(__import__("sys").modules, "pandas", __import__("pandas"))
    import sqlalchemy
    import sqlalchemy.dialects.postgresql as pg

    monkeypatch.setattr(load_mod, "get_db_engine", lambda: _Engine())
    monkeypatch.setattr(sqlalchemy, "MetaData", lambda: object())
    monkeypatch.setattr(sqlalchemy, "Table", lambda *args, **kwargs: _FakeTable())
    monkeypatch.setattr(pg, "insert", lambda table: _Stmt())

    rows = [
        {
            "symbol": "AAPL",
            "observation_date": "2026-02-14",
            "factor_name": "x",
            "factor_value": 1.0,
            "run_id": "abc",
        }
    ]
    assert load_curated(rows, dry_run=False) == 1
    assert "run_id" not in captured["records"][0]


def test_load_curated_drops_invalid_date(monkeypatch):
    class _Col:
        def __init__(self, name):
            self.name = name

    class _FakeTable:
        columns = [
            _Col("symbol"),
            _Col("observation_date"),
            _Col("factor_name"),
            _Col("factor_value"),
        ]

    class _Engine:
        def begin(self):
            raise AssertionError("should not hit DB execute when no valid rows")

    monkeypatch.setitem(__import__("sys").modules, "pandas", __import__("pandas"))
    import sqlalchemy

    monkeypatch.setattr(load_mod, "get_db_engine", lambda: _Engine())
    monkeypatch.setattr(sqlalchemy, "MetaData", lambda: object())
    monkeypatch.setattr(sqlalchemy, "Table", lambda *args, **kwargs: _FakeTable())

    rows = [{"symbol": "AAPL", "observation_date": "NaT", "factor_name": "x", "factor_value": 1.0}]
    assert load_curated(rows, dry_run=False) == 0


def test_load_financial_observations_executes_upsert(monkeypatch):
    executed = {"called": False, "constraint": None}

    class _FakeConn:
        def execute(self, stmt):
            executed["called"] = True
            executed["stmt"] = stmt

    class _Ctx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def begin(self):
            return _Ctx()

    class _Excluded:
        metric_value = "mv"
        currency = "ccy"
        period_type = "period"
        source = "src"
        as_of = "as_of"
        metric_definition = "defn"

    class _Stmt:
        excluded = _Excluded()

        def values(self, records):
            self.records = records
            return self

        def on_conflict_do_update(self, constraint, set_):
            executed["constraint"] = constraint
            executed["set_keys"] = sorted(set_.keys())
            return "UPSERT_STMT"

    monkeypatch.setattr(load_mod, "datetime", type("DT", (), {"now": staticmethod(lambda: "now")}))
    monkeypatch.setitem(__import__("sys").modules, "pandas", __import__("pandas"))

    import sqlalchemy
    import sqlalchemy.dialects.postgresql as pg

    class _Col:
        def __init__(self, name):
            self.name = name

    class _FakeTable:
        columns = [
            _Col("symbol"),
            _Col("report_date"),
            _Col("metric_name"),
            _Col("metric_value"),
            _Col("currency"),
            _Col("period_type"),
            _Col("source"),
            _Col("as_of"),
            _Col("metric_definition"),
        ]

    monkeypatch.setattr(load_mod, "get_db_engine", lambda: _Engine())
    monkeypatch.setattr(sqlalchemy, "MetaData", lambda: object())
    monkeypatch.setattr(sqlalchemy, "Table", lambda *args, **kwargs: _FakeTable())
    monkeypatch.setattr(pg, "insert", lambda table: _Stmt())

    rows = [
        {
            "symbol": "AAPL",
            "report_date": "2025-12-31",
            "metric_name": "book_value",
            "metric_value": 10.0,
            "currency": "USD",
            "period_type": "quarterly",
            "source": "alpha_vantage",
            "as_of": "2026-02-14",
            "metric_definition": "provider_reported",
        }
    ]
    out = load_mod.load_financial_observations(rows, dry_run=False)
    assert out == 1
    assert executed["called"] is True
    assert executed["constraint"] == "uniq_financial_observation"
