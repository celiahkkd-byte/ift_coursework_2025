from __future__ import annotations

"""Validate loaded pipeline data with consistent date typing across joins."""

import argparse
import math
from typing import Optional

import pandas as pd
from sqlalchemy import text

from modules.db import get_db_engine


def _normalize_date_column(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in frame.columns:
        return frame
    frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date
    return frame


def _load_latest_run_id() -> Optional[str]:
    engine = get_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT run_id
                FROM systematic_equity.pipeline_runs
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        ).first()
    return str(row[0]) if row else None


def _validate_daily_return(tolerance: float) -> tuple[int, float]:
    engine = get_db_engine()
    with engine.connect() as conn:
        price = pd.read_sql(
            text(
                """
                SELECT symbol, observation_date, factor_name, factor_value
                FROM systematic_equity.factor_observations
                WHERE factor_name IN ('adjusted_close_price', 'daily_return')
                ORDER BY symbol, observation_date
                """
            ),
            conn,
        )

    if price.empty:
        return 0, 0.0

    price = _normalize_date_column(price, "observation_date")
    piv = (
        price.pivot_table(
            index=["symbol", "observation_date"],
            columns="factor_name",
            values="factor_value",
            aggfunc="last",
        )
        .reset_index()
        .sort_values(["symbol", "observation_date"])
    )

    piv["adjusted_close_price"] = pd.to_numeric(piv["adjusted_close_price"], errors="coerce")
    piv["daily_return"] = pd.to_numeric(piv["daily_return"], errors="coerce")
    piv["prev_close"] = piv.groupby("symbol")["adjusted_close_price"].shift(1)

    valid = piv[
        (piv["adjusted_close_price"] > 0)
        & (piv["prev_close"] > 0)
        & piv["daily_return"].notna()
        & piv["observation_date"].notna()
    ].copy()
    if valid.empty:
        return 0, 0.0

    valid["recalc"] = (valid["adjusted_close_price"] / valid["prev_close"]).map(math.log)
    valid["abs_err"] = (valid["daily_return"] - valid["recalc"]).abs()
    max_abs_err = float(valid["abs_err"].max())
    if max_abs_err > tolerance:
        worst = valid.sort_values("abs_err", ascending=False).head(5)[
            ["symbol", "observation_date", "daily_return", "recalc", "abs_err"]
        ]
        raise AssertionError(
            "daily_return check failed. max_abs_err="
            f"{max_abs_err:.10f} > tolerance={tolerance}. worst_rows=\n{worst.to_string(index=False)}"
        )
    return int(len(valid)), max_abs_err


def _validate_debt_to_equity(tolerance: float) -> tuple[int, float]:
    engine = get_db_engine()
    with engine.connect() as conn:
        atomics = pd.read_sql(
            text(
                """
                SELECT symbol, report_date, metric_name, metric_value
                FROM systematic_equity.financial_observations
                WHERE metric_name IN ('total_debt', 'total_shareholder_equity')
                ORDER BY symbol, report_date
                """
            ),
            conn,
        )
        dte = pd.read_sql(
            text(
                """
                SELECT symbol, observation_date, factor_value
                FROM systematic_equity.factor_observations
                WHERE factor_name = 'debt_to_equity'
                ORDER BY symbol, observation_date
                """
            ),
            conn,
        )

    if atomics.empty or dte.empty:
        return 0, 0.0

    atomics = _normalize_date_column(atomics, "report_date")
    dte = _normalize_date_column(dte, "observation_date")

    atomics["metric_value"] = pd.to_numeric(atomics["metric_value"], errors="coerce")
    dte["factor_value"] = pd.to_numeric(dte["factor_value"], errors="coerce")

    debt = atomics[atomics["metric_name"] == "total_debt"][
        ["symbol", "report_date", "metric_value"]
    ].rename(columns={"metric_value": "total_debt"})
    equity = atomics[atomics["metric_name"] == "total_shareholder_equity"][
        ["symbol", "report_date", "metric_value"]
    ].rename(columns={"metric_value": "equity"})

    errs = []
    checked = 0
    for symbol, group in dte.groupby("symbol"):
        debt_s = debt[debt["symbol"] == symbol].sort_values("report_date")
        equity_s = equity[equity["symbol"] == symbol].sort_values("report_date")
        if debt_s.empty or equity_s.empty:
            continue
        for row in group.itertuples(index=False):
            q_end = row.observation_date
            if q_end is None:
                continue
            debt_latest = debt_s[debt_s["report_date"] <= q_end].tail(1)
            equity_latest = equity_s[equity_s["report_date"] <= q_end].tail(1)
            if debt_latest.empty or equity_latest.empty:
                continue
            ev = float(equity_latest["equity"].iloc[0])
            if not math.isfinite(ev) or ev == 0:
                continue
            expected = float(debt_latest["total_debt"].iloc[0]) / ev
            observed = float(row.factor_value)
            if not math.isfinite(expected) or not math.isfinite(observed):
                continue
            errs.append(abs(observed - expected))
            checked += 1

    if not errs:
        return 0, 0.0

    max_abs_err = float(max(errs))
    if max_abs_err > tolerance:
        raise AssertionError(
            f"debt_to_equity check failed. max_abs_err={max_abs_err:.10f} > tolerance={tolerance}"
        )
    return checked, max_abs_err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate loaded pipeline data consistency.")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Maximum accepted absolute error for recompute checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    latest_run_id = _load_latest_run_id()
    print(f"latest_run_id={latest_run_id}")

    n_ret, err_ret = _validate_daily_return(args.tolerance)
    print(f"daily_return_checked_rows={n_ret} max_abs_err={err_ret:.10f}")

    n_dte, err_dte = _validate_debt_to_equity(args.tolerance)
    print(f"debt_to_equity_checked_rows={n_dte} max_abs_err={err_dte:.10f}")

    print("validation_status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
