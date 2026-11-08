"""Figures, tables, and a Markdown report for the cluster-enhanced fallback MVP.

Personal/experimental work living outside the paper's `code/` tree. Run from
this `cluster_fallback/` directory, after `build_station_profiles.py`,
`run_cluster_fit.py`, and `run_cluster_fallback.py`:

    python make_cluster_plots.py --tag apr2024

Writes figures to cluster_fallback/clustering/output/figures/ (exploratory -- not
promoted to the paper's tracked `plots and tables/` directory) and a report
to cluster_fallback/clustering/output/REPORT_{tag}.md.
"""
from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from clustering.paths import CODE_DIR, PROJECT_ROOT  # set GDOT_PROJECT_ROOT; see clustering/paths.py
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clustering import interpret as it
from clustering import profiles as pf

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "clustering", "output")
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def fig_missingness_distribution(by_station: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(by_station["mean_completeness"], bins=30, color="#4477AA", edgecolor="black")
    ax.axvline(pf.PROFILE_COMPLETENESS_MIN, color="crimson", linestyle="--",
               label=f"completeness gate ({pf.PROFILE_COMPLETENESS_MIN})")
    ax.set_xlabel("Mean completeness across years (target month)")
    ax.set_ylabel("Number of stations")
    ax.set_title(f"Station profile completeness distribution ($n$={len(by_station)})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig_elbow_silhouette(sweep: pd.DataFrame, selected_k: int, out_path: str):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(sweep["k"], sweep["inertia"], marker="o")
    axes[0].set_xlabel("K")
    axes[0].set_ylabel("Inertia")
    axes[0].set_title("Elbow")

    axes[1].plot(sweep["k"], sweep["silhouette"], marker="o", label="Silhouette")
    axes[1].axvline(selected_k, color="crimson", linestyle="--", label=f"selected K={selected_k}")
    axes[1].set_xlabel("K")
    axes[1].set_ylabel("Silhouette score")
    axes[1].set_title("Silhouette (K selection rule: argmax)")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig_pool_size_before_after(info: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(info["pool_size_individual"], bins=30, alpha=0.5, label="Individual pool", color="#4477AA")
    ax.hist(info["pool_size_final"], bins=30, alpha=0.5, label="Final pool (after fallback)", color="#EE6677")
    ax.axvline(19, color="black", linestyle=":", label="MIN_POOL_SIZE=19")
    ax.set_xlabel("Reference pool size")
    ax.set_ylabel("Number of station-months")
    ax.set_title("Reference pool size: before vs. after cluster fallback")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig_coverage_before_after(cov: pd.DataFrame, out_path: str):
    methods = ["individual", "cluster_fallback", "still_insufficient", "no_target_data"]
    counts = [int(cov.loc[cov["method"] == m, "count"].iloc[0]) if (cov["method"] == m).any() else 0 for m in methods]
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ["#4477AA", "#66CCEE", "#CCBB44", "#BBBBBB"]
    ax.bar(methods, counts, color=colors, edgecolor="black")
    for i, c in enumerate(counts):
        ax.text(i, c + 0.5, str(c), ha="center")
    ax.set_ylabel("Number of eligible station-months")
    ax.set_title("Coverage by resolution method")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig_fallback_agreement(merged: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    methods = merged["method"].unique()
    colors = plt.get_cmap("tab10")
    for i, m in enumerate(methods):
        sub = merged[merged["method"] == m]
        ax.scatter(sub["k_star_true"], sub["k_star"], alpha=0.6, label=m, color=colors(i % 10))
    lims = [0, max(merged["k_star_true"].max(), merged["k_star"].max()) + 2]
    ax.plot(lims, lims, "k--", linewidth=1, label="y=x")
    ax.set_xlabel("True k* (individual, full pool)")
    ax.set_ylabel("Method's k*")
    ax.set_title("Fallback vs. baseline agreement with ground-truth k*")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def build_report(tag: str, profiles_df, sweep, selected_k, cluster_labels, xt, cov, overall, by_cluster, by_fc) -> str:
    n_profiled = len(profiles_df)
    n_included = int(profiles_df["included"].sum())
    sizes = cluster_labels["cluster_id"].value_counts().sort_index()

    lines = []
    lines.append(f"# Cluster-Enhanced Reference-Pool Fallback -- MVP Report ({tag})\n")
    lines.append(
        "*This is the raw, auto-generated per-run section dump. See "
        "`../REPORT.md` for the curated narrative version of these results.*\n"
    )

    lines.append("## 1. Practical problem\n")
    lines.append(
        "The existing conformal data-sufficiency pipeline requires each target "
        "station-month to have a reference pool of >= `MIN_POOL_SIZE=19` correlated "
        "companion-months. For this target month, a large share of eligible stations "
        "fail this bar and are silently dropped with no record of why. This MVP adds "
        "a traffic-pattern-cluster-based fallback to rescue some of them.\n"
    )

    lines.append("## 2. Existing pipeline and reference-pool limitation\n")
    lines.append(
        "See `coverage_before_after_{}.csv` below (Section 12) for the exact counts. "
        "`run_multi_site.run_site()` returns `None` and increments a fail counter with "
        "no persisted reason when `pool_size < MIN_POOL_SIZE` "
        "(run_multi_site.py:217-220,396-399).\n".format(tag)
    )

    lines.append("## 3-4. Data used and profile construction\n")
    lines.append(
        f"Profiles: 7-element day-of-week mean vector (raw + shape-normalized), averaged "
        f"across all available years of the target month in `complete_months_all.parquet`. "
        f"{n_profiled} stations have >=1 complete target-month; {n_included} pass the "
        f"profile-completeness gate (`PROFILE_COMPLETENESS_MIN={pf.PROFILE_COMPLETENESS_MIN}`, "
        f"measured from the daily inventory, not `complete_months_all.parquet`).\n"
    )

    lines.append("## 5. Missing-data treatment\n")
    lines.append(
        "See `missingness_by_station_{0}.csv`/`missingness_by_year_{0}.csv` and "
        "`fig_missingness_distribution.png`. Direction rows are summed (not `.max()`-deduped) "
        "so bidirectional stations aren't undercounted.\n".format(tag)
    )

    lines.append("## 6-7. Clustering method and K selection\n")
    lines.append(
        f"KMeans on the standardized shape-normalized profile. K sweep (`kmeans_sweep_{tag}.csv`) "
        f"evaluated K=2..12; selected K={selected_k} by argmax silhouette "
        f"(silhouette={sweep.loc[sweep['k']==selected_k,'silhouette'].iloc[0]:.3f}). "
        f"Calinski-Harabasz/Davies-Bouldin favor a nearby K (see raw sweep table) -- "
        f"criteria disagree somewhat; K={selected_k} was kept for parsimony, per the "
        f"documented MVP rule. **[REQUIRES PHASE 2]** for a full elbow/CH/DB agreement study.\n"
        f"Cluster sizes: {sizes.to_dict()}.\n"
    )

    lines.append("## 8. Cluster stability\n")
    lines.append(
        "**[REQUIRES PHASE 2]** -- bootstrap/subsampling stability, cross-year/cross-month "
        "ARI, and raw-vs-shape agreement were not run in this MVP pass. Only a single "
        "seeded KMeans fit (seed=42) was evaluated.\n"
    )

    lines.append("## 9. Cluster interpretation\n")
    for name, df in xt.items():
        lines.append(f"**{name}**:\n\n```\n{df.to_string()}\n```\n")
    lines.append(
        "Clusters are not a simple re-derivation of functional class, urban/rural, or "
        "volume tier -- each cluster contains a mix of all three, suggesting the "
        "shape-based grouping captures a genuinely different axis of variation "
        "(weekday/weekend pattern) than the paper's existing volume-tier stratification.\n"
    )

    lines.append("## 10. Integration with the existing pipeline\n")
    lines.append(
        "`clustering/fallback.py::run_station_month()` -- individual pool first "
        "(delegates to the same `modules/` primitives `run_multi_site.run_site()` calls); "
        "cluster-pooled fallback only when the individual pool is insufficient. Zero edits "
        "to `run_multi_site.py`. Leakage guard: asserts the augmented pool never contains "
        "the target's own row.\n"
    )

    lines.append("## 11. Validation of cluster-enhanced K*\n")
    lines.append(f"Holdout comparison against ground truth (`validation_overall_{tag}.csv`):\n\n")
    lines.append(f"```\n{overall.to_string(index=False)}\n```\n")
    lines.append(f"By cluster (`validation_by_cluster_{tag}.csv`):\n\n```\n{by_cluster.to_string(index=False)}\n```\n")
    lines.append(f"By functional class (`validation_by_fc_{tag}.csv`):\n\n```\n{by_fc.to_string(index=False)}\n```\n")

    lines.append("## 12. Coverage improvement\n")
    lines.append(f"```\n{cov.to_string(index=False)}\n```\n")

    lines.append("## 13. Sensitivity analyses\n")
    lines.append(
        "**[REQUIRES PHASE 2]** -- the 8-dimension sensitivity matrix, completeness-threshold "
        "sweep (70/80/90%), and algorithm comparison (Ward/GMM/k-medoids/DBSCAN) were not run "
        "in this MVP pass. A single default was fixed and documented for each new parameter "
        "instead (see plan).\n"
    )

    lines.append("## 14. Limitations\n")
    lines.append(
        "- Profiles are a 7-value day-of-week reduction, not full daily/realigned vectors.\n"
        "- Single target month only (no cross-month clustering stability check).\n"
        "- No `lanes`/`district` metadata exists in `site_metadata.parquet` -- not usable "
        "for crosstabs, here or in any future phase.\n"
        "- K selected by a single rule (argmax silhouette); other criteria disagree slightly.\n"
        "- Holdout validation uses a synthetic pool-truncation design, not naturally-occurring "
        "insufficient sites with known ground truth (none exist by definition).\n"
    )

    lines.append("## 15. Final recommendation\n")
    lines.append(
        "Explicit answers to the recommendation questions the MVP can support are in the "
        "chat summary accompanying this report; questions requiring Phase 2 work "
        "(algorithm choice beyond KMeans, stability across years/months, sensitivity matrix) "
        "are tagged `[REQUIRES PHASE 2]` above rather than answered speculatively.\n"
    )

    return "\n".join(lines)


def main(tag: str = "apr2024"):
    profiles_df = pd.read_parquet(os.path.join(OUTPUT_DIR, f"profiles_{tag}.parquet"))
    by_station = pd.read_csv(os.path.join(OUTPUT_DIR, f"missingness_by_station_{tag}.csv"))
    sweep = pd.read_csv(os.path.join(OUTPUT_DIR, f"kmeans_sweep_{tag}.csv"))
    cluster_labels = pd.read_csv(os.path.join(OUTPUT_DIR, f"cluster_labels_{tag}.csv"))
    info = pd.read_csv(os.path.join(OUTPUT_DIR, f"cluster_fallback_info_{tag}.csv"))
    cov = pd.read_csv(os.path.join(OUTPUT_DIR, f"coverage_before_after_{tag}.csv"))
    overall = pd.read_csv(os.path.join(OUTPUT_DIR, f"validation_overall_{tag}.csv"))
    by_cluster = pd.read_csv(os.path.join(OUTPUT_DIR, f"validation_by_cluster_{tag}.csv"))
    by_fc = pd.read_csv(os.path.join(OUTPUT_DIR, f"validation_by_fc_{tag}.csv"))
    merged = pd.read_csv(os.path.join(OUTPUT_DIR, f"validation_merged_{tag}.csv"))
    meta = pd.read_parquet(os.path.join(CODE_DIR, "data", "site_metadata.parquet"))

    included_profiles = profiles_df[profiles_df["included"]].reset_index(drop=True)
    labels_for_xt = included_profiles[["site", "volume_tier"]].merge(cluster_labels[["site", "cluster_id"]], on="site")
    xt = it.crosstab_vs_metadata(labels_for_xt, meta)

    selected_k = int(sweep.loc[sweep["silhouette"].idxmax(), "k"])

    fig_missingness_distribution(by_station, os.path.join(FIG_DIR, f"fig_missingness_distribution_{tag}.png"))
    fig_elbow_silhouette(sweep, selected_k, os.path.join(FIG_DIR, f"fig_elbow_silhouette_{tag}.png"))
    fig_pool_size_before_after(info, os.path.join(FIG_DIR, f"fig_pool_before_after_{tag}.png"))
    fig_coverage_before_after(cov, os.path.join(FIG_DIR, f"fig_coverage_before_after_{tag}.png"))
    if not merged.empty:
        fig_fallback_agreement(merged, os.path.join(FIG_DIR, f"fig_fallback_agreement_{tag}.png"))
    it.fig_cluster_map(labels_for_xt, meta, os.path.join(FIG_DIR, f"fig_cluster_map_{tag}.png"))
    it.fig_cluster_profiles(included_profiles, cluster_labels, os.path.join(FIG_DIR, f"fig_cluster_profiles_{tag}.png"))

    report = build_report(tag, profiles_df, sweep, selected_k, cluster_labels, xt, cov, overall, by_cluster, by_fc)
    report_path = os.path.join(OUTPUT_DIR, f"REPORT_{tag}.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Wrote figures to {FIG_DIR} and report to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cluster-fallback figures, tables, and report")
    parser.add_argument("--tag", type=str, default="apr2024")
    args = parser.parse_args()
    main(tag=args.tag)
