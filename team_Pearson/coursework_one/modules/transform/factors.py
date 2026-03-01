from __future__ import annotations

"""Build final factors from atomic factors persisted in PostgreSQL."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text

from modules.db import get_db_engine
from modules.output import load_curated

MARKET_ATOMIC_FACTORS = {
    "adjusted_close_price",
    "daily_return",
    "dividend_per_share",
    "momentum_1m",
    "volatility_20d",
}

ALTERNATIVE_ATOMIC_FACTORS = {
    "news_sentiment_daily",
    "news_article_count_daily",
}

FINANCIAL_ATOMIC_FACTORS = {
    "total_debt",
    "book_value",
    "shares_outstanding",
    "enterprise_ebitda",
    "enterprise_revenue",
}


def _month_ends(start: date, end: date) -> List[date]:
    out: List[date] = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        month_end = nxt - timedelta(days=1)
        if month_end <= end:
            out.append(month_end)
        cur = nxt
    return out


def _quarter_ends(start: date, end: date) -> List[date]:
    out: List[date] = []
    for year in range(start.year, end.year + 1):
        for month in (3, 6, 9, 12):
            if month == 12:
                q_end = date(year, 12, 31)
            else:
                q_end = date(year, month + 1, 1) - timedelta(days=1)
            if start <= q_end <= end:
                out.append(q_end)
    return out


def _latest_on_or_before(frame, cutoff: date, max_stale_days: Optional[int] = None):
    subset = frame[frame["observation_date"] <= cutoff]
    if subset.empty:
        return None
    row = subset.iloc[-1]
    if max_stale_days is not None and (cutoff - row["observation_date"]).days > max_stale_days:
        return None
    return row


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def _compute_dividend_yield_monthly(df, end_date: date, start_date: date) -> List[Dict[str, Any]]:
    import pandas as pd

    price = (
        df[df["factor_name"] == "adjusted_close_price"][
            ["symbol", "observation_date", "factor_value"]
        ]
        .rename(columns={"factor_value": "price"})
        .copy()
    )
    dividend = (
        df[df["factor_name"] == "dividend_per_share"][
            ["symbol", "observation_date", "factor_value"]
        ]
        .rename(columns={"factor_value": "dps"})
        .copy()
    )
    if price.empty:
        return []

    price["price"] = pd.to_numeric(price["price"], errors="coerce")
    dividend["dps"] = pd.to_numeric(dividend["dps"], errors="coerce")

    records: List[Dict[str, Any]] = []
    for symbol in sorted(price["symbol"].dropna().unique()):
        ps = price[price["symbol"] == symbol].sort_values("observation_date").copy()
        ds = dividend[dividend["symbol"] == symbol].sort_values("observation_date").copy()
        if ps.empty:
            continue
        for month_end in _month_ends(start_date, end_date):
            # Backward-looking only: month_end to month_end-3
            lb = month_end - timedelta(days=3)
            p = ps[(ps["observation_date"] >= lb) & (ps["observation_date"] <= month_end)]
            if p.empty:
                continue
            p_row = p.iloc[-1]
            px = _to_float_or_none(p_row["price"])
            if px is None or px <= 0:
                continue

            px_date = p_row["observation_date"]
            ttm_start = px_date - timedelta(days=365)
            if ds.empty:
                ttm_dps = 0.0
            else:
                ttm_slice = ds[
                    (ds["observation_date"] > ttm_start) & (ds["observation_date"] <= px_date)
                ]
                ttm_dps = float(ttm_slice["dps"].fillna(0.0).sum())

            records.append(
                {
                    "symbol": symbol,
                    "observation_date": month_end.isoformat(),
                    "factor_name": "dividend_yield",
                    "factor_value": float(ttm_dps / px),
                    "source": "factor_transform",
                    "metric_frequency": "monthly",
                    "source_report_date": px_date.isoformat(),
                }
            )
    return records


def _compute_pb_ratio_monthly(df, end_date: date, start_date: date) -> List[Dict[str, Any]]:
    import pandas as pd

    price = df[df["factor_name"] == "adjusted_close_price"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "price"})
    shares = df[df["factor_name"] == "shares_outstanding"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "shares"})
    book = df[df["factor_name"] == "book_value"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "book_value"})
    if price.empty or shares.empty or book.empty:
        return []
    price["price"] = pd.to_numeric(price["price"], errors="coerce")
    shares["shares"] = pd.to_numeric(shares["shares"], errors="coerce")
    book["book_value"] = pd.to_numeric(book["book_value"], errors="coerce")

    records: List[Dict[str, Any]] = []
    for symbol in sorted(price["symbol"].dropna().unique()):
        ps = price[price["symbol"] == symbol].sort_values("observation_date")
        ss = shares[shares["symbol"] == symbol].sort_values("observation_date")
        bs = book[book["symbol"] == symbol].sort_values("observation_date")
        if ps.empty or ss.empty or bs.empty:
            continue

        for month_end in _month_ends(start_date, end_date):
            p_row = _latest_on_or_before(
                ps[(ps["observation_date"] >= month_end - timedelta(days=3))], month_end
            )
            s_row = _latest_on_or_before(ss, month_end, max_stale_days=365)
            b_row = _latest_on_or_before(bs, month_end, max_stale_days=365)
            if p_row is None or s_row is None or b_row is None:
                continue
            p = _to_float_or_none(p_row["price"])
            s = _to_float_or_none(s_row["shares"])
            b = _to_float_or_none(b_row["book_value"])
            if p is None or s is None or b is None or p <= 0 or s <= 0 or b <= 0:
                continue
            pb = (p * s) / b
            pb = min(pb, 100.0)
            records.append(
                {
                    "symbol": symbol,
                    "observation_date": month_end.isoformat(),
                    "factor_name": "pb_ratio",
                    "factor_value": float(pb),
                    "source": "factor_transform",
                    "metric_frequency": "monthly",
                    "source_report_date": p_row["observation_date"].isoformat(),
                }
            )
    return records


def _compute_debt_to_equity_quarterly(df, end_date: date, start_date: date) -> List[Dict[str, Any]]:
    import pandas as pd

    debt = df[df["factor_name"] == "total_debt"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "debt"})
    book = df[df["factor_name"] == "book_value"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "book_value"})
    if debt.empty or book.empty:
        return []
    debt["debt"] = pd.to_numeric(debt["debt"], errors="coerce")
    book["book_value"] = pd.to_numeric(book["book_value"], errors="coerce")

    records: List[Dict[str, Any]] = []
    for symbol in sorted(debt["symbol"].dropna().unique()):
        ds = debt[debt["symbol"] == symbol].sort_values("observation_date")
        bs = book[book["symbol"] == symbol].sort_values("observation_date")
        if ds.empty or bs.empty:
            continue
        for q_end in _quarter_ends(start_date, end_date):
            d_row = _latest_on_or_before(ds, q_end, max_stale_days=270)
            b_row = _latest_on_or_before(bs, q_end, max_stale_days=270)
            if d_row is None or b_row is None:
                continue
            debt_v = _to_float_or_none(d_row["debt"])
            book_v = _to_float_or_none(b_row["book_value"])
            if debt_v is None or book_v is None or book_v <= 0:
                continue
            records.append(
                {
                    "symbol": symbol,
                    "observation_date": q_end.isoformat(),
                    "factor_name": "debt_to_equity",
                    "factor_value": float(debt_v / book_v),
                    "source": "factor_transform",
                    "metric_frequency": "quarterly",
                    "source_report_date": max(
                        d_row["observation_date"], b_row["observation_date"]
                    ).isoformat(),
                }
            )
    return records


def _compute_ebitda_margin(df, end_date: date, start_date: date) -> List[Dict[str, Any]]:
    import pandas as pd

    ebitda = df[df["factor_name"] == "enterprise_ebitda"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "ebitda"})
    revenue = df[df["factor_name"] == "enterprise_revenue"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "revenue"})
    if ebitda.empty or revenue.empty:
        return []
    ebitda["ebitda"] = pd.to_numeric(ebitda["ebitda"], errors="coerce")
    revenue["revenue"] = pd.to_numeric(revenue["revenue"], errors="coerce")

    records: List[Dict[str, Any]] = []
    for symbol in sorted(ebitda["symbol"].dropna().unique()):
        es = ebitda[ebitda["symbol"] == symbol].sort_values("observation_date")
        rs = revenue[revenue["symbol"] == symbol].sort_values("observation_date")
        if es.empty or rs.empty:
            continue
        for q_end in _quarter_ends(start_date, end_date):
            e_row = _latest_on_or_before(es, q_end, max_stale_days=365)
            r_row = _latest_on_or_before(rs, q_end, max_stale_days=365)
            if e_row is None or r_row is None:
                continue
            ebitda_v = _to_float_or_none(e_row["ebitda"])
            rev_v = _to_float_or_none(r_row["revenue"])
            if ebitda_v is None or rev_v is None or rev_v <= 0:
                continue
            records.append(
                {
                    "symbol": symbol,
                    "observation_date": q_end.isoformat(),
                    "factor_name": "ebitda_margin",
                    "factor_value": float(ebitda_v / rev_v),
                    "source": "factor_transform",
                    "metric_frequency": "quarterly",
                    "source_report_date": max(
                        e_row["observation_date"], r_row["observation_date"]
                    ).isoformat(),
                }
            )
    return records


def _compute_sentiment_30d_avg(df, end_date: date, start_date: date) -> List[Dict[str, Any]]:
    import pandas as pd

    sentiment_atomic = df[df["factor_name"] == "news_sentiment_daily"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "sentiment"})
    count_atomic = df[df["factor_name"] == "news_article_count_daily"][
        ["symbol", "observation_date", "factor_value"]
    ].rename(columns={"factor_value": "article_count"})
    if sentiment_atomic.empty and count_atomic.empty:
        return []

    records: List[Dict[str, Any]] = []
    symbols = set(sentiment_atomic["symbol"].dropna().unique())
    symbols.update(count_atomic["symbol"].dropna().unique())
    for symbol in sorted(symbols):
        ds = sentiment_atomic[sentiment_atomic["symbol"] == symbol].sort_values("observation_date").copy()
        ds["sentiment"] = pd.to_numeric(ds["sentiment"], errors="coerce")
        ds["observation_ts"] = pd.to_datetime(ds["observation_date"], errors="coerce")
        ds = ds.dropna(subset=["sentiment", "observation_ts"])
        # Step 1: daily sentiment (or multiple rows per day) -> daily mean.
        daily_sentiment = (
            ds.groupby(["symbol", "observation_ts"], as_index=False)["sentiment"]
            .mean()
            .sort_values("observation_ts")
        )
        # Step 1b: daily article count atomic.
        daily_count_rows = count_atomic[count_atomic["symbol"] == symbol].copy()
        daily_count_rows["observation_ts"] = pd.to_datetime(
            daily_count_rows["observation_date"], errors="coerce"
        )
        daily_count_rows["article_count"] = pd.to_numeric(
            daily_count_rows["article_count"], errors="coerce"
        )
        daily_count_rows = daily_count_rows.dropna(subset=["observation_ts"])
        if not daily_count_rows.empty:
            daily_count = (
                daily_count_rows.groupby(["symbol", "observation_ts"], as_index=False)[
                    "article_count"
                ]
                .sum()
                .sort_values("observation_ts")
            )
        else:
            daily_count = pd.DataFrame(columns=["symbol", "observation_ts", "article_count"])

        # Step 2: fill missing calendar days with 0.0 sentiment.
        full_dates = pd.date_range(start=start_date, end=end_date, freq="D")
        daily = daily_sentiment.set_index("observation_ts").reindex(full_dates)
        daily.index.name = "observation_ts"
        daily["symbol"] = symbol
        daily["sentiment"] = daily["sentiment"].fillna(0.0)

        daily_count_filled = daily_count.set_index("observation_ts").reindex(full_dates)
        daily["article_count"] = pd.to_numeric(
            daily_count_filled["article_count"], errors="coerce"
        ).fillna(0.0)

        daily = daily.reset_index()
        daily["observation_date"] = daily["observation_ts"].dt.date
        # Step 3: true 30-day rolling stats.
        daily["sentiment_30d"] = daily.rolling("30D", on="observation_ts", min_periods=1)[
            "sentiment"
        ].mean()
        daily["article_count_30d"] = daily.rolling("30D", on="observation_ts", min_periods=1)[
            "article_count"
        ].sum()
        for month_end in _month_ends(start_date, end_date):
            row = _latest_on_or_before(daily, month_end, max_stale_days=0)
            if row is None:
                # zero-news fallback
                records.append(
                    {
                        "symbol": symbol,
                        "observation_date": month_end.isoformat(),
                        "factor_name": "sentiment_30d_avg",
                        "factor_value": 0.0,
                        "source": "factor_transform",
                        "metric_frequency": "monthly",
                        "source_report_date": month_end.isoformat(),
                    }
                )
                records.append(
                    {
                        "symbol": symbol,
                        "observation_date": month_end.isoformat(),
                        "factor_name": "article_count_30d",
                        "factor_value": 0.0,
                        "source": "factor_transform",
                        "metric_frequency": "monthly",
                        "source_report_date": month_end.isoformat(),
                    }
                )
                continue
            v = max(-1.0, min(1.0, float(row["sentiment_30d"])))
            records.append(
                {
                    "symbol": symbol,
                    "observation_date": month_end.isoformat(),
                    "factor_name": "sentiment_30d_avg",
                    "factor_value": float(v),
                    "source": "factor_transform",
                    "metric_frequency": "monthly",
                    "source_report_date": row["observation_date"].isoformat(),
                }
            )
            records.append(
                {
                    "symbol": symbol,
                    "observation_date": month_end.isoformat(),
                    "factor_name": "article_count_30d",
                    "factor_value": float(row["article_count_30d"]),
                    "source": "factor_transform",
                    "metric_frequency": "monthly",
                    "source_report_date": row["observation_date"].isoformat(),
                }
            )
    return records


def compute_final_factor_records(
    atomic_records: Iterable[Dict[str, Any]],
    run_date: str,
    backfill_years: int,
) -> List[Dict[str, Any]]:
    """Compute final factors from atomic records."""
    import pandas as pd

    records = list(atomic_records)
    if not records:
        return []

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return []
    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce").dt.date
    df = df.dropna(subset=["observation_date", "symbol", "factor_name"])
    if df.empty:
        return []

    end_date = datetime.strptime(run_date, "%Y-%m-%d").date()
    lookback_days = max(1, int(round(365.25 * max(int(backfill_years), 1))))
    start_date = end_date - timedelta(days=lookback_days)
    data_start_date = start_date - timedelta(days=370)
    df = df[
        (df["observation_date"] >= data_start_date) & (df["observation_date"] <= end_date)
    ].copy()
    if df.empty:
        return []

    out: List[Dict[str, Any]] = []
    out.extend(_compute_dividend_yield_monthly(df, end_date, start_date))
    out.extend(_compute_pb_ratio_monthly(df, end_date, start_date))
    out.extend(_compute_debt_to_equity_quarterly(df, end_date, start_date))
    out.extend(_compute_ebitda_margin(df, end_date, start_date))
    out.extend(_compute_sentiment_30d_avg(df, end_date, start_date))
    return out


def _load_atomic_records_from_postgres(
    run_date: str,
    backfill_years: int,
    symbols: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    end_date = datetime.strptime(run_date, "%Y-%m-%d").date()
    lookback_days = max(1, int(round(365.25 * max(int(backfill_years), 1))))
    start_date = end_date - timedelta(days=lookback_days)
    query_start_date = start_date - timedelta(days=370)
    params: Dict[str, Any] = {
        "start_date": query_start_date.isoformat(),
        "end_date": run_date,
    }

    symbol_clause = ""
    if symbols:
        params["symbols"] = [str(s).strip().upper() for s in symbols if str(s).strip()]
        if params["symbols"]:
            symbol_clause = " AND symbol = ANY(:symbols)"

    market_sql = text(
        f"""
        SELECT symbol, observation_date, factor_name, factor_value, source, metric_frequency, source_report_date
        FROM systematic_equity.factor_observations
        WHERE observation_date BETWEEN :start_date AND :end_date
          AND factor_name = ANY(:factor_names)
          {symbol_clause}
        ORDER BY symbol, observation_date, factor_name
        """
    )
    market_params = dict(params)
    market_params["factor_names"] = sorted(MARKET_ATOMIC_FACTORS.union(ALTERNATIVE_ATOMIC_FACTORS))

    financial_sql = text(
        f"""
        SELECT
            symbol,
            report_date AS observation_date,
            metric_name AS factor_name,
            metric_value AS factor_value,
            source,
            period_type AS metric_frequency,
            as_of AS source_report_date
        FROM systematic_equity.financial_observations
        WHERE report_date BETWEEN :start_date AND :end_date
          AND metric_name = ANY(:metric_names)
          {symbol_clause}
        ORDER BY symbol, report_date, metric_name
        """
    )
    financial_params = dict(params)
    financial_params["metric_names"] = sorted(FINANCIAL_ATOMIC_FACTORS)

    fallback_financial_sql = text(
        f"""
        SELECT symbol, observation_date, factor_name, factor_value, source, metric_frequency, source_report_date
        FROM systematic_equity.factor_observations
        WHERE observation_date BETWEEN :start_date AND :end_date
          AND factor_name = ANY(:factor_names)
          {symbol_clause}
        ORDER BY symbol, observation_date, factor_name
        """
    )
    fallback_financial_params = dict(params)
    fallback_financial_params["factor_names"] = sorted(FINANCIAL_ATOMIC_FACTORS)

    engine = get_db_engine()
    with engine.connect() as conn:
        market_rows = conn.execute(market_sql, market_params).mappings().all()
        try:
            financial_rows = conn.execute(financial_sql, financial_params).mappings().all()
        except Exception:
            financial_rows = conn.execute(
                fallback_financial_sql, fallback_financial_params
            ).mappings().all()

    rows = [dict(r) for r in market_rows]
    rows.extend(dict(r) for r in financial_rows)
    rows.sort(
        key=lambda r: (
            str(r.get("symbol") or ""),
            str(r.get("observation_date") or ""),
            str(r.get("factor_name") or ""),
        )
    )
    return rows


def build_and_load_final_factors(
    run_date: str,
    backfill_years: int,
    *,
    symbols: Optional[List[str]] = None,
    dry_run: bool = False,
) -> int:
    """Build final factors from atomic factors in Postgres and load them back."""
    atomic_records = _load_atomic_records_from_postgres(
        run_date=run_date, backfill_years=backfill_years, symbols=symbols
    )
    final_records = compute_final_factor_records(
        atomic_records=atomic_records,
        run_date=run_date,
        backfill_years=backfill_years,
    )
    if not final_records:
        return 0
    return load_curated(final_records, dry_run=dry_run)
