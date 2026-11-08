"""Station-month completeness / missingness measurement.

`code/data/complete_months_all.parquet` cannot be used to measure missingness:
by construction (see `data_loader.build_complete_months`, `build_complete_months.py`)
it contains ONLY months where every calendar day is present and non-incomplete —
gaps are already filtered out before that file exists. To see real gaps we go one
layer down, to the daily inventory `code/cache/full_daily_volumes.parquet`, which
has one row per (site, direction, date) for every day ever observed, including
incomplete months.
"""
from __future__ import annotations

import calendar
import os

import numpy as np
import pandas as pd

from .paths import CACHE_DIR  # <GDOT_PROJECT_ROOT>/code/cache

# Matches the incomplete-day convention already used throughout data_loader.py
# (e.g. data_loader.py:110,184,258 — all gate on n_bins/expected_bins < 0.95).
INCOMPLETE_BIN_RATIO = 0.95


def load_full_daily(cache_dir: str = CACHE_DIR) -> pd.DataFrame:
    """Load the daily-inventory parquet (site, direction, date, volume, n_bins, expected_bins, source)."""
    path = os.path.join(cache_dir, "full_daily_volumes.parquet")
    return pd.read_parquet(path)


def collapse_directions(fv: pd.DataFrame, how: str = "sum") -> pd.DataFrame:
    """Collapse multiple direction rows per (site, date) into one daily total.

    Deliberate, documented divergence from `build_complete_months.py:26-30`, which
    dedupes (site, date) via `.max()` — silently keeping only the larger-volume
    direction and discarding the other for the ~87% of stations that are
    bidirectional (confirmed: 247/284 sites carry 2 direction values in this
    checkout). For cluster profiles we want each station's TOTAL traffic, matching
    how MADT/volume-tier are already interpreted elsewhere in the pipeline, so we
    sum across directions instead.

    A day's `quality_ok` is False if ANY contributing direction row falls below
    the existing INCOMPLETE_BIN_RATIO bar (0.95), matching data_loader.py's
    per-row `incomplete` semantics extended to the collapsed day.
    """
    if how != "sum":
        raise NotImplementedError(f"collapse_directions: how={how!r} not implemented")

    fv = fv.copy()
    fv["bin_ratio"] = fv["n_bins"] / fv["expected_bins"].replace(0, np.nan)
    grouped = fv.groupby(["site", "date"], as_index=False).agg(
        volume=("volume", "sum"),
        n_bins=("n_bins", "sum"),
        expected_bins=("expected_bins", "sum"),
        min_bin_ratio=("bin_ratio", "min"),
        n_directions=("direction", "nunique"),
    )
    grouped["quality_ok"] = grouped["min_bin_ratio"] >= INCOMPLETE_BIN_RATIO
    return grouped


def station_month_completeness(fv_daily: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """One row per site observed in `fv_daily` for (year, month).

    Columns: site, year, month, days_in_month, n_days_observed (any row present),
    n_days_quality_ok (present AND not incomplete), completeness_raw
    (n_days_observed / days_in_month), completeness (n_days_quality_ok / days_in_month).

    Sites with zero rows for this (year, month) are absent from the output
    entirely (not zero-filled) — the caller decides how to treat true absence
    vs. partial presence.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    sub = fv_daily[
        (fv_daily["date"].dt.year == year) & (fv_daily["date"].dt.month == month)
    ]
    if sub.empty:
        return pd.DataFrame(
            columns=[
                "site", "year", "month", "days_in_month",
                "n_days_observed", "n_days_quality_ok",
                "completeness_raw", "completeness",
            ]
        )
    agg = sub.groupby("site").agg(
        n_days_observed=("date", "nunique"),
        n_days_quality_ok=("quality_ok", "sum"),
    ).reset_index()
    agg["year"] = year
    agg["month"] = month
    agg["days_in_month"] = days_in_month
    agg["completeness_raw"] = agg["n_days_observed"] / days_in_month
    agg["completeness"] = agg["n_days_quality_ok"] / days_in_month
    return agg[
        ["site", "year", "month", "days_in_month",
         "n_days_observed", "n_days_quality_ok",
         "completeness_raw", "completeness"]
    ]


def completeness_across_years(
    fv_daily: pd.DataFrame, month: int, years: list[int] | None = None
) -> pd.DataFrame:
    """Long df: one row per (site, year) for a fixed calendar `month` across `years`.

    Used both as the "missingness by year" report and as the direct input to
    the multi-year composite profile in `profiles.py`.
    """
    if years is None:
        years = sorted(fv_daily["date"].dt.year.unique().tolist())
    frames = [station_month_completeness(fv_daily, y, month) for y in years]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def completeness_across_months(fv_daily: pd.DataFrame, year: int) -> pd.DataFrame:
    """Long df: one row per (site, month) for a fixed `year` across all 12 months."""
    frames = [station_month_completeness(fv_daily, year, m) for m in range(1, 13)]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def missingness_report(fv_daily: pd.DataFrame, target_month: int) -> dict[str, pd.DataFrame]:
    """Bundle the three missingness views the plan calls for, all for `target_month`.

    - by_station: per-site mean/min/max completeness and n_years_observed, across
      all years that have any data for `target_month`.
    - by_year: per-year mean completeness across sites (network-wide trend).
    - raw: the underlying (site, year) long df, for computing the completeness
      distribution histogram downstream.
    """
    raw = completeness_across_years(fv_daily, target_month)
    if raw.empty:
        empty = pd.DataFrame()
        return {"by_station": empty, "by_year": empty, "raw": raw}

    by_station = raw.groupby("site").agg(
        n_years_observed=("year", "nunique"),
        mean_completeness=("completeness", "mean"),
        min_completeness=("completeness", "min"),
        max_completeness=("completeness", "max"),
    ).reset_index()

    by_year = raw.groupby("year").agg(
        n_sites=("site", "nunique"),
        mean_completeness=("completeness", "mean"),
        median_completeness=("completeness", "median"),
    ).reset_index()

    return {"by_station": by_station, "by_year": by_year, "raw": raw}
