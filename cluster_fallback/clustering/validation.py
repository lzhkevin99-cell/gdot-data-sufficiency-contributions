"""Holdout validation of the cluster-enhanced fallback against ground truth.

Design (non-circular by construction): a site's TRUE k*/point-estimate quality
comes from its real, full, untruncated companion list -- computed once, before
any truncation. We then deterministically shrink that same site's companion
list until its *individual* pool drops below `MIN_POOL_SIZE`, forcing the
`cluster_fallback` branch, and compare the fallback's k* against the
already-known truth. Two cheap baseline fallbacks (same-functional-class pooled,
all-eligible-sites pooled) are run through the identical truncate-and-compare
procedure for comparison.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import run_multi_site as rms
from . import fallback as fb


def shrink_companions_to_insufficient(
    target_site: str,
    target_year: int,
    target_month: int,
    companions: list[str],
    cm_detrended: pd.DataFrame,
    min_pool_size: int = rms.MIN_POOL_SIZE,
    seed: int = 42,
) -> tuple[list[str], int]:
    """Deterministically truncate `companions` until the individual pool for
    (target_site, target_year, target_month) drops below `min_pool_size`.

    Shuffles once with a fixed seed (reproducible, but not biased toward
    whichever companions happen to sort first alphabetically/by FC), then
    removes companions one at a time from the end until the pool clears the
    floor. Returns (truncated_companions, resulting_pool_size).
    """
    rng = np.random.default_rng(seed)
    remaining = list(companions)
    rng.shuffle(remaining)

    for n_keep in range(len(remaining), -1, -1):
        trial = remaining[:n_keep]
        result = rms.build_pool_fast(target_site, target_year, target_month, trial, cm_detrended)
        pool_size = result["pool_size"] if result else 0
        if pool_size < min_pool_size:
            return trial, pool_size
    return [], 0


def baseline_same_fc_pooled(
    target_site: str, target_year: int, target_month: int,
    meta: pd.DataFrame, cm_detrended: pd.DataFrame, R: int,
) -> dict:
    """Baseline fallback: pool from every other site sharing the same
    `fc_code` (no urban/rural match, no ±1 window, no cluster) -- a coarser,
    cluster-free companion rule to check whether clustering adds value beyond
    the simplest possible functional-class pooling.
    """
    fc_row = meta.loc[meta["site"] == target_site, "fc_code"]
    if fc_row.empty or pd.isna(fc_row.iloc[0]):
        return dict(site=target_site, method="baseline_same_fc", pool_size=0, sim=None)
    fc = fc_row.iloc[0]
    same_fc_sites = meta.loc[(meta["fc_code"] == fc) & (meta["site"] != target_site), "site"].tolist()

    result = rms.build_pool_fast(target_site, target_year, target_month, same_fc_sites, cm_detrended)
    if result is None or result["pool_size"] < rms.MIN_POOL_SIZE:
        return dict(
            site=target_site, method="baseline_same_fc",
            pool_size=result["pool_size"] if result else 0, sim=None,
        )
    sim_out = fb._simulate_tail(target_site, result, R)
    return dict(site=target_site, method="baseline_same_fc", pool_size=result["pool_size"], sim=sim_out)


def baseline_all_pooled(
    target_site: str, target_year: int, target_month: int,
    all_sites: list[str], cm_detrended: pd.DataFrame, R: int,
) -> dict:
    """Baseline fallback: pool from every other eligible site network-wide,
    no functional-class/urban-rural/cluster matching at all.
    """
    companions = [s for s in all_sites if s != target_site]
    result = rms.build_pool_fast(target_site, target_year, target_month, companions, cm_detrended)
    if result is None or result["pool_size"] < rms.MIN_POOL_SIZE:
        return dict(
            site=target_site, method="baseline_all_pooled",
            pool_size=result["pool_size"] if result else 0, sim=None,
        )
    sim_out = fb._simulate_tail(target_site, result, R)
    return dict(site=target_site, method="baseline_all_pooled", pool_size=result["pool_size"], sim=sim_out)


def k_star_from_sim(sim_out: dict | None, site: str) -> pd.DataFrame:
    """One row per mechanism: k* for a single site's `_simulate_tail` output.

    Reuses `run_multi_site.summarize_multi`/`k_star_per_site_mech` unchanged --
    both are generic (site, mechanism, k) aggregators, not part of the
    statistical algorithm itself, so importing them is not a re-implementation.
    """
    if sim_out is None:
        return pd.DataFrame(columns=["site", "mechanism", "k_star"])
    summary = rms.summarize_multi(sim_out["raw"])
    return rms.k_star_per_site_mech(summary)


def error_by(merged: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """MAE/RMSE/bias/correlation of `error` (= method's k* - truth's k*),
    grouped by `method` and the given breakdown column(s).
    """
    def _agg(g):
        return pd.Series({
            "n": len(g),
            "mae": g["error"].abs().mean(),
            "rmse": float(np.sqrt((g["error"] ** 2).mean())),
            "bias": g["error"].mean(),
            "corr": g["k_star"].corr(g["k_star_true"]) if g["k_star"].nunique() > 1 else np.nan,
        })
    return merged.groupby(["method"] + group_cols).apply(_agg).reset_index()


def compare_methods_vs_truth(
    kstar_long: pd.DataFrame, truth_method: str = "individual"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`kstar_long`: one row per (site, method, mechanism, k_star, ...breakdown
    columns like cluster_id/fc_code/pool_size_bucket/centroid_distance...).

    Returns (overall_by_method, merged_long) where `merged_long` has one row
    per (site, method, mechanism) with an `error` column, ready for further
    `error_by()` breakdowns or agreement-plot scatterplots.
    """
    truth = kstar_long[kstar_long["method"] == truth_method][["site", "mechanism", "k_star"]].rename(
        columns={"k_star": "k_star_true"}
    )
    other = kstar_long[kstar_long["method"] != truth_method]
    merged = other.merge(truth, on=["site", "mechanism"], how="inner")
    merged = merged.dropna(subset=["k_star", "k_star_true"]).copy()
    merged["error"] = merged["k_star"] - merged["k_star_true"]
    overall = error_by(merged, [])
    return overall, merged
