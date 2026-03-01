from __future__ import annotations

"""Structured extractor (Source A).

This module fetches market/fundamental data for symbols, persists raw payloads
to MinIO, and returns records aligned to the pipeline's curated schema.
"""

import json
import logging
import os
import time
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def load_config(config_path: str = "config/conf.yaml") -> Dict[str, Any]:
    """Load YAML configuration from disk.

    Parameters
    ----------
    config_path:
        Path to YAML config file.

    Returns
    -------
    dict[str, Any]
        Parsed config dictionary. Returns an empty dict when file is missing.
    """
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _download_price_history(symbol: str, years_back: int, max_retries: int = 3):
    """Download price history from yfinance (fallback provider)."""
    import yfinance as yf

    period = f"{max(1, int(years_back))}y"
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period, auto_adjust=False)
            if history is None or history.empty:
                raise ValueError(f"No history returned for symbol={symbol}")
            return ticker, history
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                raise RuntimeError(f"source_a history download failed for {symbol}: {exc}") from exc

    raise RuntimeError(f"source_a history download failed for {symbol}: {last_error}")


def _download_price_history_alpha_vantage(
    symbol: str, years_back: int, api_key: str, timeout_seconds: int = 30
):
    """Download adjusted daily prices from Alpha Vantage."""
    _ = years_back  # endpoint returns full adjusted history; trimmed downstream by run_date
    base_url = "https://www.alphavantage.co/query"
    query = urlencode(
        {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": api_key,
        }
    )
    with urlopen(f"{base_url}?{query}", timeout=timeout_seconds) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if "Error Message" in payload:
        raise RuntimeError(payload["Error Message"])
    if "Note" in payload:
        raise RuntimeError(payload["Note"])

    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise RuntimeError(f"Alpha Vantage returned no daily data for {symbol}")

    rows: List[Dict[str, Any]] = []
    for obs_date, values in series.items():
        rows.append(
            {
                "observation_date": obs_date,
                "Close": float(values.get("5. adjusted close") or values.get("4. close") or 0.0),
                "Dividends": float(values.get("7. dividend amount") or 0.0),
            }
        )
    history = pd.DataFrame(rows)
    if history.empty:
        raise RuntimeError(f"Alpha Vantage history dataframe empty for {symbol}")

    history["observation_date"] = pd.to_datetime(history["observation_date"])
    history = history.set_index("observation_date").sort_index()
    return None, history


def _extract_total_debt(ticker: Any) -> Optional[float]:
    try:
        balance_sheet = ticker.quarterly_balance_sheet
        debt_fields = ["Total Debt", "TotalDebt", "Long Term Debt", "LongTermDebt"]
        for field in debt_fields:
            if field in balance_sheet.index:
                value = balance_sheet.loc[field].iloc[0]
                if value is None:
                    return None
                return float(value)
    except Exception:  # pragma: no cover - upstream schema dependent
        return None
    return None


def _minio_config(config: Dict[str, Any]) -> Dict[str, Any]:
    minio_cfg = dict(config.get("minio") or {})
    minio_cfg["endpoint"] = os.getenv("MINIO_ENDPOINT", minio_cfg.get("endpoint"))
    minio_cfg["access_key"] = os.getenv("MINIO_ACCESS_KEY", minio_cfg.get("access_key"))
    minio_cfg["secret_key"] = os.getenv("MINIO_SECRET_KEY", minio_cfg.get("secret_key"))
    minio_cfg["bucket"] = os.getenv("MINIO_BUCKET", minio_cfg.get("bucket"))
    endpoint = str(minio_cfg.get("endpoint", "")).replace("http://", "").replace("https://", "")
    minio_cfg["endpoint"] = endpoint
    return minio_cfg


def _raw_object_path(symbol: str, run_date: str) -> str:
    return (
        "raw/source_a/pricing_fundamentals/"
        f"run_date={run_date}/year={run_date[:4]}/symbol={symbol}.json"
    )


def _load_raw_from_minio(
    config: Dict[str, Any], symbol: str, run_date: str
) -> Optional[Dict[str, Any]]:
    minio_cfg = _minio_config(config)
    required = ["endpoint", "access_key", "secret_key", "bucket"]
    if not all(minio_cfg.get(k) for k in required):
        return None

    try:
        from minio import Minio

        client = Minio(
            endpoint=minio_cfg["endpoint"],
            access_key=minio_cfg["access_key"],
            secret_key=minio_cfg["secret_key"],
            secure=minio_cfg.get("secure", False),
        )
        obj = client.get_object(minio_cfg["bucket"], _raw_object_path(symbol, run_date))
        try:
            return json.loads(obj.read().decode("utf-8"))
        finally:
            obj.close()
            obj.release_conn()
    except Exception:
        return None


def _save_raw_to_minio(
    config: Dict[str, Any],
    symbol: str,
    run_date: str,
    payload: Dict[str, Any],
) -> None:
    minio_cfg = _minio_config(config)
    required = ["endpoint", "access_key", "secret_key", "bucket"]
    if not all(minio_cfg.get(k) for k in required):
        return

    try:
        from minio import Minio

        client = Minio(
            endpoint=minio_cfg["endpoint"],
            access_key=minio_cfg["access_key"],
            secret_key=minio_cfg["secret_key"],
            secure=minio_cfg.get("secure", False),
        )
        bucket = minio_cfg["bucket"]
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        object_path = _raw_object_path(symbol, run_date)
        data = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        client.put_object(
            bucket,
            object_path,
            data=BytesIO(data),
            length=len(data),
            content_type="application/json",
        )
    except Exception as exc:  # pragma: no cover - external service dependent
        logger.warning("source_a raw archive skipped for %s: %r", symbol, exc)


def _compute_momentum_1m(close_series: pd.Series) -> pd.Series:
    return close_series / close_series.shift(20) - 1.0


def _compute_volatility_20d(close_series: pd.Series) -> pd.Series:
    returns = close_series.pct_change()
    return returns.rolling(window=20).std()


def _build_technical_records(
    symbol: str, history: Any, frequency: str, source_label: str
) -> List[Dict[str, Any]]:
    if len(history) < 20:
        return []

    close_series = history.get("Close")
    if close_series is None:
        return []
    close_series = pd.to_numeric(close_series, errors="coerce").dropna()
    close_series = close_series[close_series > 0]
    if len(close_series) < 20:
        return []

    momentum = _compute_momentum_1m(close_series)
    volatility = _compute_volatility_20d(close_series)

    records: List[Dict[str, Any]] = []
    for idx, value in momentum.dropna().items():
        observation_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
        records.append(
            {
                "symbol": symbol,
                "observation_date": observation_date,
                "factor_name": "momentum_1m",
                "value": float(value),
                "source": source_label,
                "frequency": frequency,
            }
        )
    for idx, value in volatility.dropna().items():
        observation_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
        records.append(
            {
                "symbol": symbol,
                "observation_date": observation_date,
                "factor_name": "volatility_20d",
                "value": float(value),
                "source": source_label,
                "frequency": frequency,
            }
        )
    return records


def _build_records_from_history(
    symbol: str,
    history: Any,
    run_date: str,
    frequency: str,
    total_debt: Optional[float],
    source_label: str = "source_a",
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for idx, row in history.iterrows():
        observation_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]

        close = row.get("Close")
        dividends = row.get("Dividends")

        records.append(
            {
                "symbol": symbol,
                "observation_date": observation_date,
                "factor_name": "adjusted_close_price",
                "value": None if close is None else float(close),
                "source": source_label,
                "frequency": frequency,
            }
        )
        records.append(
            {
                "symbol": symbol,
                "observation_date": observation_date,
                "factor_name": "dividend_per_share",
                "value": None if dividends is None else float(dividends),
                "source": source_label,
                "frequency": frequency,
            }
        )

    records.append(
        {
            "symbol": symbol,
            "observation_date": run_date,
            "factor_name": "total_debt",
            "value": total_debt,
            "source": source_label,
            "frequency": frequency,
        }
    )

    return records


def _resolve_alpha_key(config: Dict[str, Any]) -> str:
    api_cfg = config.get("api") or {}
    value = (
        os.getenv("ALPHA_VANTAGE_API_KEY")
        or os.getenv("ALPHA_VANTAGE_KEY")
        or api_cfg.get("alpha_vantage_key")
        or ""
    )
    value = str(value).strip()
    if value in {"", "YOUR_KEY", "YOUR_API_KEY_HERE"}:
        return ""
    return value


def _select_source_order(config: Dict[str, Any]) -> List[str]:
    source_cfg = config.get("source_a") or {}
    primary = str(source_cfg.get("primary_source", "alpha_vantage")).strip().lower()
    fallback = bool(source_cfg.get("enable_yfinance_fallback", True))
    order = [primary]
    if fallback and primary != "yfinance":
        order.append("yfinance")
    if not order:
        return ["alpha_vantage", "yfinance"]
    return order


def _history_from_payload(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("history") or []
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    if "Date" in frame.columns:
        idx_col = "Date"
    elif "observation_date" in frame.columns:
        idx_col = "observation_date"
    else:
        idx_col = frame.columns[0]
    frame[idx_col] = pd.to_datetime(frame[idx_col])
    return frame.set_index(idx_col).sort_index()


def _download_with_provider(
    symbol: str, years_back: int, config: Dict[str, Any]
) -> tuple[str, Any, pd.DataFrame]:
    errors: List[str] = []
    alpha_key = _resolve_alpha_key(config)
    for source in _select_source_order(config):
        try:
            if source == "alpha_vantage":
                if not alpha_key:
                    raise RuntimeError("alpha_vantage key missing")
                ticker, history = _download_price_history_alpha_vantage(
                    symbol, years_back, alpha_key
                )
            elif source == "yfinance":
                ticker, history = _download_price_history(symbol, years_back)
            else:
                raise RuntimeError(f"unsupported provider: {source}")
            return source, ticker, history
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    raise RuntimeError(f"all providers failed for {symbol}; details={errors}")


def extract_source_a(
    symbols: List[str],
    run_date: str,
    backfill_years: int,
    frequency: str,
    config: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Extract Source A records for a symbol list.

    Parameters
    ----------
    symbols:
        Target symbol list supplied by upstream universe selection.
    run_date:
        Pipeline run date in ``YYYY-MM-DD`` format.
    backfill_years:
        Historical lookback window in years.
    frequency:
        Scheduling frequency label (daily/weekly/monthly/quarterly/annual).
    config:
        Optional in-memory config. If omitted, config is loaded from file.

    Returns
    -------
    list[dict[str, Any]]
        Extracted records in the pre-normalized schema used by downstream
        normalize/quality/load stages.
    """
    if os.getenv("CW1_TEST_MODE") == "1":
        return [
            {
                "symbol": symbol,
                "observation_date": run_date,
                "factor_name": "source_a_metric",
                "value": 1.0,
                "source": "source_a_test",
                "frequency": frequency,
            }
            for symbol in symbols
        ]

    cfg = config or load_config("config/conf.yaml")
    target_symbols = list(symbols or [])
    if not target_symbols:
        return []
    source_cfg = cfg.get("source_a") or {}
    use_cache = bool(source_cfg.get("use_cache", False))

    records: List[Dict[str, Any]] = []
    for symbol in target_symbols:
        try:
            symbol_records: List[Dict[str, Any]] = []
            payload = _load_raw_from_minio(cfg, symbol, run_date) if use_cache else None
            provider_source = "cache_replay"
            ticker = None

            if payload:
                history = _history_from_payload(payload)
                total_debt = payload.get("total_debt")
                provider_source = str(payload.get("source_used") or "cache_replay")
            else:
                provider_source, ticker, history = _download_with_provider(
                    symbol, backfill_years, cfg
                )
                total_debt = _extract_total_debt(ticker)
                payload = {
                    "symbol": symbol,
                    "run_date": run_date,
                    "rows": int(len(history)),
                    "history": history.reset_index().to_dict(orient="records"),
                    "total_debt": total_debt,
                    "source_used": provider_source,
                }
                _save_raw_to_minio(cfg, symbol, run_date, payload)

            symbol_records.extend(
                _build_records_from_history(
                    symbol=symbol,
                    history=history,
                    run_date=run_date,
                    frequency=frequency,
                    total_debt=total_debt,
                    source_label=provider_source,
                )
            )
            symbol_records.extend(
                _build_technical_records(
                    symbol=symbol,
                    history=history,
                    frequency=frequency,
                    source_label=provider_source,
                )
            )
            records.extend(symbol_records)
        except Exception as exc:
            logger.error("source_a failed for %s: %r", symbol, exc)

    return records


if __name__ == "__main__":
    today = datetime.today().strftime("%Y-%m-%d")
    out = extract_source_a(["AAPL"], run_date=today, backfill_years=1, frequency="daily")
    print(f"records={len(out)}")
