"""Run the cluster-enhanced fallback over every eligible station-month, then a
non-circular holdout validation against ground truth.

Personal/experimental work living outside the paper's `code/` tree -- reads
`code/data/`, `code/modules/`, and `code/run_multi_site.py` read-only (via a
sys.path shim below) and never edits anything under `code/`. Run from this
`cluster_fallback/` directory, after `build_station_profiles.py` and `run_cluster_fit.py`:

    python run_cluster_fallback.py --month 4 --year 2024 --tag apr2024

This is the clustering-analogue of `run_multi_site.py`: same eligibility rule,
same constants (imported, not redefined), but additionally records which
method (individual / cluster_fallback / still_insufficient / no_target_data)
produced each result -- something `run_multi_site.py` never persists today.

Writes to cluster_fallback/clustering/output/:
    cluster_fallback_info_{tag}.csv     one row per eligible site: method, pool
                                         sizes, cluster_id, n_siblings_added
    cluster_fallback_kstar_{tag}.csv    one row per (site, mechanism): k_star
    coverage_before_after_{tag}.csv     coverage accounting table
    validation_overall_{tag}.csv        MAE/RMSE/bias/corr by method (holdout)
    validation_by_cluster_{tag}.csv     same, broken down by cluster_id
    validation_by_fc_{tag}.csv          same, broken down by functional class
    validation_merged_{tag}.csv         long per-(site,method,mechanism) rows,
                                         for the agreement scatterplot
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from clustering.paths import CODE_DIR, PROJECT_ROOT  # set GDOT_PROJECT_ROOT; see clustering/paths.py
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

import numpy as np
import pandas as pd

import run_multi_site as rms
from modules import preprocess as pp
from clustering import fallback as fb
from clustering import validation as val

DATA_DIR = os.path.join(CODE_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "clustering", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("run_cluster_fallback")


def load_eligible_sites(cm_detrended: pd.DataFrame, target_year: int, target_month: int) -> list[str]:
    """Identical eligibility rule to run_multi_site.main() (complete target
    month + >= MIN_HISTORY_MONTHS of own history) -- reused, not re-derived,
    so the eligible-site population here matches the Step 0 baseline exactly.
    """
    target_months = cm_detrended[
        (cm_detrended["year"] == target_year) & (cm_detrended["month"] == target_month)
    ]
    eligible = sorted(target_months["site"].unique())
    site_counts = cm_detrended.groupby("site").size()
    return [s for s in eligible if site_counts.get(s, 0) >= rms.MIN_HISTORY_MONTHS]


def run_all_sites(
    eligible_sites: list[str], target_year: int, target_month: int,
    meta: pd.DataFrame, cm_detrended: pd.DataFrame, cluster_labels: pd.DataFrame, R: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    info_rows = []
    kstar_frames = []
    t0 = time.time()
    for i, site in enumerate(eligible_sites):
        r = fb.run_station_month(site, target_year, target_month, meta, cm_detrended, cluster_labels, R=R)
        info_rows.append({k: v for k, v in r.items() if k != "sim"})
        kstar_frames.append(val.k_star_from_sim(r["sim"], site))
        if (i + 1) % 25 == 0:
            log.info(f"  {i+1}/{len(eligible_sites)} sites done ({time.time()-t0:.0f}s)")

    info = pd.DataFrame(info_rows)
    kstar = pd.concat(kstar_frames, ignore_index=True) if kstar_frames else pd.DataFrame()
    return info, kstar


def coverage_table(info: pd.DataFrame, n_eligible: int) -> pd.DataFrame:
    counts = info["method"].value_counts().reindex(
        ["individual", "cluster_fallback", "still_insufficient", "no_target_data"], fill_value=0
    )
    counts["n_eligible"] = n_eligible
    counts["residual_check"] = n_eligible - counts[
        ["individual", "cluster_fallback", "still_insufficient", "no_target_data"]
    ].sum()
    return counts.rename("count").reset_index().rename(columns={"index": "method"})


def run_holdout_validation(
    info: pd.DataFrame, target_year: int, target_month: int,
    meta: pd.DataFrame, cm_detrended: pd.DataFrame, cluster_labels: pd.DataFrame,
    eligible_sites: list[str], R: int, n_holdout: int, min_pool_for_holdout: int, seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Non-circular holdout: pick sites already resolved as `individual` with
    a pool comfortably above MIN_POOL_SIZE, get their TRUE k* from the
    already-computed full-pool result, then re-run with an artificially
    truncated companion list to force cluster_fallback/baselines, and compare.
    """
    candidates = info[(info["method"] == "individual") & (info["pool_size_individual"] >= min_pool_for_holdout)]
    rng = np.random.default_rng(seed)
    holdout_sites = list(rng.choice(candidates["site"].values, size=min(n_holdout, len(candidates)), replace=False))
    log.info(f"Holdout validation set: {len(holdout_sites)} sites (pool_size >= {min_pool_for_holdout})")

    all_sites_pool = eligible_sites  # for baseline_all_pooled

    rows = []
    kstar_frames = []
    for site in holdout_sites:
        # Truth: full, untruncated companion list (already what info/kstar
        # computed for this site's "individual" row -- recomputed here for a
        # self-contained validation pass).
        companions_full = rms.find_companions(site, meta)
        truth = fb.run_station_month(site, target_year, target_month, meta, cm_detrended, cluster_labels, R=R)
        kstar_frames.append(val.k_star_from_sim(truth["sim"], site).assign(method="individual"))

        shrunk, forced_pool = val.shrink_companions_to_insufficient(
            site, target_year, target_month, companions_full, cm_detrended
        )
        fallback_res = fb.run_station_month(
            site, target_year, target_month, meta, cm_detrended, cluster_labels, R=R,
            companions_override=shrunk,
        )
        kstar_frames.append(val.k_star_from_sim(fallback_res["sim"], site).assign(method="cluster_fallback"))

        same_fc = val.baseline_same_fc_pooled(site, target_year, target_month, meta, cm_detrended, R)
        kstar_frames.append(val.k_star_from_sim(same_fc["sim"], site).assign(method="baseline_same_fc"))

        all_pooled = val.baseline_all_pooled(site, target_year, target_month, all_sites_pool, cm_detrended, R)
        kstar_frames.append(val.k_star_from_sim(all_pooled["sim"], site).assign(method="baseline_all_pooled"))

        cl_row = cluster_labels.loc[cluster_labels["site"] == site]
        rows.append(dict(
            site=site,
            fc_code=meta.loc[meta["site"] == site, "fc_code"].iloc[0] if not meta[meta["site"] == site].empty else None,
            cluster_id=int(cl_row.iloc[0]["cluster_id"]) if not cl_row.empty else None,
            centroid_distance=float(cl_row.iloc[0]["centroid_distance"]) if not cl_row.empty and "centroid_distance" in cl_row else None,
            pool_size_individual_full=truth["pool_size_individual"],
            forced_pool_size=forced_pool,
            fallback_method_achieved=fallback_res["method"],
        ))

    kstar_long = pd.concat(kstar_frames, ignore_index=True) if kstar_frames else pd.DataFrame()
    site_meta = pd.DataFrame(rows)
    kstar_long = kstar_long.merge(site_meta, on="site", how="left")

    overall, merged = val.compare_methods_vs_truth(kstar_long, truth_method="individual")
    by_cluster = val.error_by(merged, ["cluster_id"])
    by_fc = val.error_by(merged, ["fc_code"])
    return overall, by_cluster, by_fc, merged


def main(target_year: int = 2024, target_month: int = 4, tag: str = "apr2024", R: int = 50, n_holdout: int = 20):
    meta = pd.read_parquet(os.path.join(DATA_DIR, "site_metadata.parquet"))
    cm_all = pd.read_parquet(os.path.join(DATA_DIR, "complete_months_all.parquet"))

    log.info("Recomputing holiday correction + detrending (identical to run_multi_site.py steps 0-1)")
    cm_corr = rms.apply_holiday_correction(cm_all)
    cm_detrended = pp.detrend(cm_corr, baseline_year=rms.BASELINE_YEAR)

    eligible_sites = load_eligible_sites(cm_detrended, target_year, target_month)
    log.info(f"Eligible sites for {target_year}-{target_month:02d}: {len(eligible_sites)}")

    cluster_labels = pd.read_csv(os.path.join(OUTPUT_DIR, f"cluster_labels_{tag}.csv"))

    log.info(f"Running fallback wrapper over {len(eligible_sites)} sites (R={R})...")
    info, kstar = run_all_sites(eligible_sites, target_year, target_month, meta, cm_detrended, cluster_labels, R)

    info.to_csv(os.path.join(OUTPUT_DIR, f"cluster_fallback_info_{tag}.csv"), index=False)
    kstar.to_csv(os.path.join(OUTPUT_DIR, f"cluster_fallback_kstar_{tag}.csv"), index=False)

    cov = coverage_table(info, len(eligible_sites))
    cov.to_csv(os.path.join(OUTPUT_DIR, f"coverage_before_after_{tag}.csv"), index=False)
    log.info(f"Coverage accounting:\n{cov.to_string(index=False)}")

    log.info(f"Running holdout validation (n_holdout={n_holdout})...")
    overall, by_cluster, by_fc, merged = run_holdout_validation(
        info, target_year, target_month, meta, cm_detrended, cluster_labels,
        eligible_sites, R=max(R, rms.R_FULL // 2), n_holdout=n_holdout, min_pool_for_holdout=38,
    )
    overall.to_csv(os.path.join(OUTPUT_DIR, f"validation_overall_{tag}.csv"), index=False)
    by_cluster.to_csv(os.path.join(OUTPUT_DIR, f"validation_by_cluster_{tag}.csv"), index=False)
    by_fc.to_csv(os.path.join(OUTPUT_DIR, f"validation_by_fc_{tag}.csv"), index=False)
    merged.to_csv(os.path.join(OUTPUT_DIR, f"validation_merged_{tag}.csv"), index=False)
    log.info(f"Validation (overall, vs individual truth):\n{overall.to_string(index=False)}")

    log.info(f"All outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cluster-enhanced reference-pool fallback")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--month", type=int, default=4)
    parser.add_argument("--tag", type=str, default="apr2024")
    parser.add_argument("--R", type=int, default=50, help="Replications per (mechanism,k) cell")
    parser.add_argument("--n-holdout", type=int, default=20)
    args = parser.parse_args()
    main(target_year=args.year, target_month=args.month, tag=args.tag, R=args.R, n_holdout=args.n_holdout)
