# Cluster-pooled reference-pool fallback (MVP)

**Interpretation of the results: [`REPORT.md`](REPORT.md).** This file covers the problem, the layout,
and how to run the code.

> **Scope:** a self-directed learning exercise. The fallback was not adopted and was never presented as
> a change to the paper.

## Problem

The paper's multi-site pipeline (`code/run_multi_site.py` in the project repo) requires each target
station-month to have a reference pool of at least `MIN_POOL_SIZE = 19` correlated companion-months.
For April 2024, only **84 of 185** eligible stations clear this bar. The other **101**, mostly
low-volume rural sites, are silently dropped: the function returns `None` and increments a counter, and
nothing records which stations failed or why.

This MVP adds a fallback on top of the paper's code, without changing it. Stations are grouped into
clusters by the shape of their weekly (day-of-week) traffic. When a station-month's individual pool is
too small, the fallback retries with the pool enlarged by stations from the same cluster before giving
up.

## Result, briefly

- **Coverage:** 84 → 95 of 185 eligible stations (45% → 51%).
- **Accuracy:** in a non-circular holdout, the fix is **worse than simply pooling all
  same-functional-class stations** (MAE 3.48 vs 2.91 days), so it is not adopted.
- **Shape-normalization:** load-bearing. Clustering on raw volumes agrees with the shape clustering at
  ARI = 0.028.

Full tables, figures and the reasoning behind them are in [`REPORT.md`](REPORT.md).

## Layout

```
clustering/                  core library
  paths.py                     locates the project checkout via GDOT_PROJECT_ROOT
  missingness.py               completeness from code/cache/full_daily_volumes.parquet
  profiles.py                  station traffic-pattern profiles (day-of-week reduction)
  cluster_fit.py               K-means + K-selection diagnostics
  interpret.py                 crosstabs vs site metadata + Georgia cluster map
  fallback.py                  run_station_month(), the integration wrapper
  validation.py                holdout benchmark + baseline fallbacks + error metrics
  output/                      figures and REPORT_apr2024.md (raw per-run dump); data tables are
                               regenerated locally and not published
build_station_profiles.py    steps 1-2: profiles + missingness
run_cluster_fit.py           step 3: K-means fit
run_cluster_fallback.py      steps 5-6: fallback wrapper + holdout validation
make_cluster_plots.py        step 7: figures, tables, REPORT_{tag}.md
REPORT.md                    curated interpretation of the results
```

## Running

This code reuses the paper's unmodified `code/modules/`, `code/run_multi_site.py` and shipped data
(`code/data/`, `code/cache/`). Those are not in this repo, so point `GDOT_PROJECT_ROOT` at a checkout of
the project repository (the directory that contains `code/`):

```bash
export GDOT_PROJECT_ROOT=/path/to/gdot-project
cd cluster_fallback
python build_station_profiles.py --month 4 --tag apr2024
python run_cluster_fit.py --tag apr2024
python run_cluster_fallback.py --month 4 --year 2024 --tag apr2024 --R 50 --n-holdout 20
python make_cluster_plots.py --tag apr2024
```

`run_cluster_fallback.py --R 50` runs sequentially and takes about 30–40 minutes for the full 185-site
pass plus the 20-site holdout. Reduce `--R` or `--n-holdout` for a quick smoke test. Re-running
`run_cluster_fit.py` reproduces the original run's `cluster_labels_apr2024.csv`,
`cluster_labels_raw_apr2024.csv` and `kmeans_sweep_apr2024.csv` byte-for-byte.

The scripts write their data tables (`*.csv`, `*.parquet`) to `clustering/output/`. Those tables are
derived from GDoT records, so they are not published in this repo; only the figures and reports are.

## Scope: a staged MVP, not the full specification

The scope is deliberately narrow: one target month, K-means only, and two baselines. Deferred work is
tagged `[REQUIRES PHASE 2]` in `clustering/output/REPORT_apr2024.md`:

- Algorithm comparison (Ward hierarchical, GMM, k-medoids, DBSCAN).
- The full 8-dimension sensitivity matrix and a completeness-threshold sweep (70/80/90%).
- Multi-year, growth-adjusted composite profiles (a simple unweighted multi-year mean is used here).
- Cluster stability analysis (bootstrap, cross-year and cross-month ARI).
- Additional target months (July 2024, December 2023).

Two thresholds have no precedent in the paper's codebase. They are fixed as documented defaults, not
tuned:

- `PROFILE_COMPLETENESS_MIN = 0.90` (`clustering/profiles.py`).
- Direction lanes are collapsed by `sum` rather than the `.max()` dedup used in the paper's
  `build_complete_months.py` (`clustering/missingness.py`).

`site_metadata.parquet` has no `lanes` or `district` column, so crosstabs against those fields are not
possible with the data on hand.
