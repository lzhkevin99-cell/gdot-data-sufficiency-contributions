"""Fit KMeans on station profiles and select K.

Personal/experimental work living outside the paper's `code/` tree. Run from
this `cluster_fallback/` directory, after `build_station_profiles.py`:

    python run_cluster_fit.py --tag apr2024

Writes to cluster_fallback/clustering/output/:
    kmeans_sweep_{tag}.csv       one row per K: inertia/silhouette/CH/DB/cluster sizes
    cluster_labels_{tag}.csv     site, cluster_id, centroid_distance (shape-profile clustering)
    cluster_labels_raw_{tag}.csv site, cluster_id (raw-volume profile clustering, for comparison only)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from clustering.paths import CODE_DIR, PROJECT_ROOT  # set GDOT_PROJECT_ROOT; see clustering/paths.py
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

import pandas as pd

from clustering import cluster_fit as cf
from clustering import profiles as pf

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "clustering", "output")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("run_cluster_fit")


def main(tag: str = "apr2024"):
    profiles_df = pd.read_parquet(os.path.join(OUTPUT_DIR, f"profiles_{tag}.parquet"))
    profiles_df = profiles_df[profiles_df["included"]].reset_index(drop=True)
    log.info(f"Clustering {len(profiles_df)} stations that pass the completeness gate")

    # Primary (used by the fallback wrapper): shape-normalized profile --
    # grouping by traffic PATTERN, not overall volume (which would just
    # re-derive the existing volume-tier stratification already in the paper).
    X_shape = pf.shape_matrix(profiles_df)
    sweep = cf.fit_kmeans_sweep(X_shape)
    k = cf.select_k(sweep)
    log.info(f"K sweep (shape profile):\n{sweep.to_string()}")
    log.info(f"Selected K={k} (argmax silhouette)")

    labels, centroids, scaler, km = cf.fit_final(X_shape, k)
    dist = cf.centroid_distances(X_shape, labels, scaler, km)

    cluster_labels = profiles_df[["site"]].copy()
    cluster_labels["cluster_id"] = labels
    cluster_labels["centroid_distance"] = dist
    sizes = cluster_labels["cluster_id"].value_counts().sort_index()
    log.info(f"Cluster sizes:\n{sizes.to_string()}")

    # Secondary (comparison only, NOT used by the fallback wrapper): raw-volume
    # profile clustering, expected to re-derive the volume-tier stratification.
    X_raw = pf.raw_matrix(profiles_df)
    sweep_raw = cf.fit_kmeans_sweep(X_raw)
    k_raw = cf.select_k(sweep_raw)
    labels_raw, _, _, _ = cf.fit_final(X_raw, k_raw)
    cluster_labels_raw = profiles_df[["site"]].copy()
    cluster_labels_raw["cluster_id"] = labels_raw

    sweep.to_csv(os.path.join(OUTPUT_DIR, f"kmeans_sweep_{tag}.csv"), index=False)
    cluster_labels.to_csv(os.path.join(OUTPUT_DIR, f"cluster_labels_{tag}.csv"), index=False)
    cluster_labels_raw.to_csv(os.path.join(OUTPUT_DIR, f"cluster_labels_raw_{tag}.csv"), index=False)
    log.info(f"Wrote kmeans_sweep_{tag}.csv, cluster_labels_{tag}.csv, cluster_labels_raw_{tag}.csv to {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fit KMeans on station traffic profiles")
    parser.add_argument("--tag", type=str, default="apr2024")
    args = parser.parse_args()
    main(tag=args.tag)
