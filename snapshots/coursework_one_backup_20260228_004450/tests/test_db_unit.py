import pytest

import modules.db.db_connection as db_connection
import modules.db.universe as universe
from modules.db.universe import get_company_count, get_company_universe


def test_universe_test_mode_list(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    symbols = get_company_universe(3)
    assert symbols == ["AAPL", "MSFT", "GOOG"]


def test_universe_test_mode_count(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    assert get_company_count() >= 5


def test_universe_minimum_limit_in_test_mode(monkeypatch):
    monkeypatch.setenv("CW1_TEST_MODE", "1")
    symbols = get_company_universe(0)
    assert len(symbols) == 1
    assert symbols[0] == "AAPL"


def test_db_engine_success(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(db_connection, "create_engine", lambda url: sentinel)
    assert db_connection.get_db_engine() is sentinel


def test_db_engine_failure_wrapped(monkeypatch):
    def _boom(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(db_connection, "create_engine", _boom)
    with pytest.raises(RuntimeError, match="engine initialization failed"):
        db_connection.get_db_engine()


class _FakeResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def fetchall(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class _FakeConn:
    def __init__(self, rows=None, scalar=None, fail_first=False):
        self.rows = rows
        self.scalar = scalar
        self.fail_first = fail_first
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("first table missing")
        self.sql = sql
        self.params = params
        if self.rows is not None:
            return _FakeResult(rows=self.rows)
        return _FakeResult(scalar=self.scalar)


class _FakeEngine:
    def __init__(self, rows=None, scalar=None, fail_first=False):
        self.rows = rows
        self.scalar = scalar
        self.fail_first = fail_first

    def connect(self):
        return _FakeConn(rows=self.rows, scalar=self.scalar, fail_first=self.fail_first)


def test_universe_reads_from_db_in_non_test_mode(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)
    monkeypatch.setattr(universe, "get_db_engine", lambda: _FakeEngine(rows=[("AAPL",), ("MSFT",)]))

    out = universe.get_company_universe(2)
    assert out == ["AAPL", "MSFT"]


def test_company_count_reads_from_db_in_non_test_mode(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)
    monkeypatch.setattr(universe, "get_db_engine", lambda: _FakeEngine(scalar=321))

    out = universe.get_company_count()
    assert out == 321


def test_universe_falls_back_to_equity_static_when_company_static_missing(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)
    monkeypatch.setattr(
        universe, "get_db_engine", lambda: _FakeEngine(rows=[("AAPL",)], fail_first=True)
    )

    out = universe.get_company_universe(2)
    assert out == ["AAPL"]


def test_universe_country_allowlist_passes_filter_params(monkeypatch):
    monkeypatch.delenv("CW1_TEST_MODE", raising=False)

    captured = {"params": None}

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            captured["params"] = params

            class _R:
                def fetchall(self_non):
                    return [("AAPL",)]

            return _R()

    class _Engine2:
        def connect(self):
            return _Conn()

    monkeypatch.setattr(universe, "get_db_engine", lambda: _Engine2())
    out = universe.get_company_universe(5, country_allowlist=["US", "GB"])
    assert out == ["AAPL"]
    assert captured["params"]["country_0"] == "US"
    assert captured["params"]["country_1"] == "GB"
