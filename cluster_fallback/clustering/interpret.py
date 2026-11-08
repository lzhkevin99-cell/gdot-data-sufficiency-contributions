"""Cluster interpretation: crosstabs against station metadata + a Georgia cluster map."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import profiles as pf

log = logging.getLogger("clustering.interpret")

# Reused verbatim from run_multi_site.py:430-434 -- not a new threshold.
VOLUME_TIER_BINS = [0, 5000, 15000, float("inf")]
VOLUME_TIER_LABELS = ["Low (<5k)", "Medium (5-15k)", "High (>15k)"]


def add_volume_tier(profiles_df: pd.DataFrame) -> pd.DataFrame:
    """Approximate MADT for `target_month` as the mean of the raw DOW profile,
    then bin it using the exact bins run_multi_site.py already uses for its own
    volume_tier column, so cluster-vs-tier crosstabs are directly comparable to
    the paper's existing volume-tier stratification.
    """
    out = profiles_df.copy()
    raw_cols = [f"raw_{d}" for d in pf.DOW_LABELS]
    out["madt_approx"] = out[raw_cols].mean(axis=1)
    out["volume_tier"] = pd.cut(
        out["madt_approx"], bins=VOLUME_TIER_BINS, labels=VOLUME_TIER_LABELS
    )
    return out


def crosstab_vs_metadata(labels_df: pd.DataFrame, meta: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Cluster x fc_code, cluster x urban_rural, cluster x volume_tier crosstabs.

    `labels_df` must have `site`, `cluster_id`, and (from `add_volume_tier`)
    `volume_tier`. Only metadata columns confirmed to exist in
    `site_metadata.parquet` are used -- no `lanes`/`district` (not present).
    """
    merged = labels_df.merge(
        meta[["site", "fc_code", "fc_label", "urban_rural"]], on="site", how="left"
    )
    return {
        "cluster_x_fc": pd.crosstab(merged["cluster_id"], merged["fc_label"]),
        "cluster_x_ur": pd.crosstab(merged["cluster_id"], merged["urban_rural"]),
        "cluster_x_volume_tier": pd.crosstab(merged["cluster_id"], merged["volume_tier"]),
    }


def fig_cluster_map(labels_df: pd.DataFrame, meta: pd.DataFrame, out_path: str):
    """Georgia map of clustered stations, coloured by cluster (categorical).

    Adapted from `make_multi_site_plots.fig_site_map` (same geopandas + TIGER
    boundary pattern), with `c=merged["madt"]` + `LogNorm` swapped for a discrete
    colormap over `cluster_id` and a categorical legend instead of a colorbar.

    Unlike the original, the geopandas import itself is wrapped in the
    availability check (not just the TIGER download), since this environment has
    neither geopandas installed nor network access to fetch shapefiles -- both
    failure modes fall back to a plain lon/lat scatter with no boundaries.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    merged = labels_df.merge(meta[["site", "latitude", "longitude"]], on="site", how="left")
    merged = merged.dropna(subset=["latitude", "longitude"])

    has_geo = False
    try:
        import geopandas as gpd

        try:
            states = gpd.read_file(
                "https://www2.census.gov/geo/tiger/TIGER2023/STATE/tl_2023_us_state.zip"
            )
            ga_state = states[states["STATEFP"] == "13"]
            counties = gpd.read_file(
                "https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_us_county.zip"
            )
            ga_counties = counties[counties["STATEFP"] == "13"]
            has_geo = True
        except Exception as e:
            log.warning(f"Could not load TIGER shapefiles ({e}); falling back to plain scatter")
    except ImportError:
        log.warning("geopandas not installed; falling back to plain lon/lat scatter")

    fig, ax = plt.subplots(figsize=(7, 8))

    if has_geo:
        ga_state.boundary.plot(ax=ax, color="black", linewidth=1.2)
        ga_counties.boundary.plot(ax=ax, color="#cccccc", linewidth=0.3)

    cluster_ids = sorted(merged["cluster_id"].unique())
    cmap = plt.get_cmap("tab10")
    for i, cid in enumerate(cluster_ids):
        sub = merged[merged["cluster_id"] == cid]
        ax.scatter(
            sub["longitude"], sub["latitude"],
            color=cmap(i % 10), s=40, edgecolors="black", linewidths=0.4,
            label=f"Cluster {cid} (n={len(sub)})", zorder=5,
        )
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor=cmap(i % 10),
               markeredgecolor="black", markersize=8, label=f"Cluster {cid} (n={(merged['cluster_id']==cid).sum()})")
        for i, cid in enumerate(cluster_ids)
    ], loc="lower right", fontsize=8, title="Traffic-pattern cluster")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"CCS stations by traffic-pattern cluster ($n$={len(merged)})")
    ax.set_aspect("equal")
    ax.grid(False)

    if has_geo:
        bounds = ga_state.total_bounds
        margin = 0.15
        ax.set_xlim(bounds[0] - margin, bounds[2] + margin)
        ax.set_ylim(bounds[1] - margin, bounds[3] + margin)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig_cluster_profiles(profiles_df: pd.DataFrame, labels_df: pd.DataFrame, out_path: str, use_shape: bool = True):
    """Small-multiples: one panel per cluster, individual station profiles shown
    lightly behind the cluster centroid (mean) profile.
    """
    import matplotlib.pyplot as plt

    merged = profiles_df.merge(labels_df[["site", "cluster_id"]], on="site", how="inner")
    cols = [f"{'shape' if use_shape else 'raw'}_{d}" for d in pf.DOW_LABELS]
    cluster_ids = sorted(merged["cluster_id"].unique())

    fig, axes = plt.subplots(1, len(cluster_ids), figsize=(4 * len(cluster_ids), 4), sharey=True)
    if len(cluster_ids) == 1:
        axes = [axes]
    for ax, cid in zip(axes, cluster_ids):
        sub = merged[merged["cluster_id"] == cid]
        for _, row in sub.iterrows():
            ax.plot(pf.DOW_LABELS, row[cols].to_numpy(dtype=float), color="grey", alpha=0.25, linewidth=0.8)
        centroid = sub[cols].mean(axis=0).to_numpy(dtype=float)
        ax.plot(pf.DOW_LABELS, centroid, color="crimson", linewidth=2.5, marker="o")
        ax.set_title(f"Cluster {cid} (n={len(sub)})")
        ax.set_xlabel("Day of week")
    axes[0].set_ylabel("Shape-normalized volume" if use_shape else "Mean daily volume")
    fig.suptitle("Cluster centroid profiles (grey = individual stations)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
