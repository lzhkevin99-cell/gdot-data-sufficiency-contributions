# Cluster-Enhanced Reference-Pool Fallback — Interpretation Report

> **Scope:** a self-directed learning exercise. The fallback was not adopted and was never presented as
> a change to the paper; the recommendations below are notes on what further work would require.

Target month: **April 2024** (matches the paper's primary case study). All
numbers below are from the actual run in `clustering/output/` (`--R 50`, `--n-holdout 20`,
`seed=42`). Figures are in `clustering/output/figures/`; this file is the narrative
read of what they mean. The data tables named below (`*.csv`, `*.parquet`) are produced
by the scripts but are not published in this repository, because they are derived from
GDoT records.

**This is the curated version.** `clustering/output/REPORT_{tag}.md` is the raw,
auto-generated companion `make_cluster_plots.py` writes fresh every run --
read this file for the interpretation, that one if you want the un-edited,
per-run section dump.

## 1. What problem this addresses

The paper's existing pipeline (`code/run_multi_site.py`) needs a reference
pool of at least 19 correlated companion-months to run its conformal
sufficiency test on a target station-month. For April 2024, **101 of 185
eligible stations (55%)** fail that bar and are silently dropped — the script
returns `None` and increments a counter, with no record of which stations or
why (`run_multi_site.py:217-220,396-399`). Those are disproportionately
low-volume rural sites — exactly the stations GDoT most needs a data-
sufficiency answer for.

This work asks: can we recover some of those 101 by pooling in *other
stations with a similar traffic pattern* when a station's own pool is too
small, instead of just giving up?

## 2. Methods used

**Traffic-pattern profiles.** Each station is reduced to a 7-element
day-of-week mean-volume vector, averaged across every available year of
April in `complete_months_all.parquet`. Two versions are built: raw (actual
volumes) and shape-normalized (divided by the station's own mean) — clustering
uses the shape version, so grouping reflects weekday/weekend *pattern*, not
just how busy a road is (raw-volume clustering would just re-derive the
existing volume-tier split already in the paper).

**Missingness, measured properly.** `complete_months_all.parquet` only
contains complete months by definition, so it can't show gaps. Missingness is
instead computed from the daily inventory (`code/cache/full_daily_volumes.parquet`,
1.1M rows), collapsing each station's direction-lanes by summing (not the
`.max()` dedup the existing pipeline uses elsewhere — chosen so two-way
stations aren't undercounted). Of 273 stations with any April history, mean
completeness across years is 0.90 (median 0.97); 74 fall below a 0.90 gate and
are excluded from clustering (`fig_missingness_distribution_apr2024.png`).

**Clustering.** K-means on the standardized shape profile, K swept 2–12
(`fig_elbow_silhouette_apr2024.png`, `kmeans_sweep_apr2024.csv`). Silhouette
peaks at **K=3** (0.406) — Calinski-Harabasz and Davies-Bouldin lean slightly
toward K=4–6, so the criteria don't fully agree; K=3 was kept for parsimony,
per the documented MVP rule (argmax silhouette). 194 stations pass the
completeness gate and get clustered; sizes are **126 / 12 / 56**.

**Integration.** A new wrapper (`clustering/fallback.py::run_station_month`)
tries the individual pool first — reusing the existing pipeline's own
`find_companions()` and `build_pool_fast()` unchanged. Only if that pool is
below 19 does it retry with the target's cluster-mates added to the companion
list, then runs the identical downstream simulation. Nothing in
`run_multi_site.py` was edited; the simulation-orchestration tail was
reimplemented against the same `modules/` primitives instead, so the paper's
"verified reproducible" pipeline is never touched. An assertion guards against
the target's own data leaking into its augmented pool.

**Validation.** Non-circular by construction: 20 stations that already have a
comfortably large individual pool (≥38) are used as ground truth (their real,
full-pool k\* is known). Each is then artificially shrunk below the 19-pool
floor and re-solved three ways — cluster fallback, and two simpler baselines
(pool from all same-functional-class stations; pool from every eligible
station network-wide) — and compared back against the known truth.

## 3. What we focused on (and explicitly didn't)

This is a **staged MVP**, not the full spec: one target month, K-means only,
one profile representation, a single K-selection rule, two baselines (not
four). Deferred to a later pass, tagged `[REQUIRES PHASE 2]` in
`clustering/output/REPORT_apr2024.md`: Ward/GMM/k-medoids/DBSCAN comparison, the full
8-dimension sensitivity matrix, multi-year growth-adjusted profiles, cluster
stability testing (bootstrap/ARI across years and months), and running against
July 2024 / December 2023. Two new thresholds with no precedent elsewhere in
the codebase were fixed as documented defaults rather than tuned:
`PROFILE_COMPLETENESS_MIN=0.90` and direction-collapse via `sum`.

## 4. Results — coverage

| Method | Count | Share of 185 eligible |
|---|---|---|
| `individual` (existing pipeline, unchanged) | 84 | 45.4% |
| `cluster_fallback` (rescued) | **11** | **5.9%** |
| `still_insufficient` (cluster didn't help enough) | 90 | 48.6% |
| `no_target_data` | 0 | 0% |

(`coverage_before_after_apr2024.csv`, `fig_coverage_before_after_apr2024.png`,
`fig_pool_before_after_apr2024.png`)

Cluster pooling raises resolved coverage from **84 → 95 stations (45% → 51%)**.
The 11 rescued sites had individual pools as small as 3–18 months; adding
their ~125 cluster-0 siblings pushed them past the 19-month floor. The
remaining 90 unresolved sites mostly either have no cluster label (failed the
completeness gate) or belong to a cluster too small/dissimilar to help —
cluster augmentation is not a universal fix, it closes part of the gap, not
all of it.

## 5. Results — validation (does the fallback's k\* agree with truth?)

Holdout comparison against the 20 sites' known individual-pool k\*
(`validation_overall_apr2024.csv`):

| Method | n (site×mechanism) | MAE (days) | RMSE | Bias | Corr. |
|---|---|---|---|---|---|
| `cluster_fallback` | 100 | 3.48 | 4.85 | +0.68 | 0.735 |
| `baseline_same_fc` | 96 | 2.91 | 4.30 | −1.26 | 0.818 |
| `baseline_all_pooled` | 108 | 3.18 | 4.89 | +2.10 | 0.787 |

**Honest reading: in this MVP, cluster pooling does not clearly beat the
simplest baseline.** Pooling from all same-functional-class stations
(`baseline_same_fc`) has lower error and higher correlation with ground truth
than the cluster-based fallback. Cluster pooling does beat the crudest
baseline (pool everything, no matching at all) on bias and is competitive on
RMSE, but the 7-value day-of-week shape signal isn't adding clear value over
functional class alone at K=3 — plausibly because functional class is already
a strong proxy for weekday/weekend shape, or because the shape reduction is
too coarse (see Phase 2: full daily profiles).

Breakdown (`validation_by_cluster_apr2024.csv`, `validation_by_fc_apr2024.csv`):
error is concentrated in the dominant cluster (cluster 0, n≈94–96; MAE 3.6 for
cluster_fallback) and in functional class 4 (MAE 4.5, vs. 2.1 for class 3) —
worth a note that mid-tier arterial/collector roads are where this approach is
currently weakest, not the extremes.

## 6. Cluster interpretation

Clusters are **not** a re-derivation of functional class, urban/rural, or
volume tier — each of the three clusters contains a mix of all of them
(`fig_cluster_map_apr2024.png`, `fig_cluster_profiles_apr2024.png`). That
confirms the shape-based grouping is capturing a genuinely different axis
(weekday/weekend pattern shape) than the paper's existing stratification — but
per §5, that different axis isn't yet translating into better k\* recovery
than functional class alone.

**Is the volume-normalization step actually necessary?** Checked directly:
`cluster_labels_raw_apr2024.csv` (K-means on the raw, non-normalized profile,
computed by `run_cluster_fit.py` but never previously checked against
anything) agrees with the shape-based clustering at **ARI = 0.028** — i.e.
essentially unrelated groupings. So yes, normalizing is doing real work, not
a cosmetic step. The specific reason: raw clustering doesn't cleanly
reproduce the paper's Low/Medium/High volume tiers either (ARI=0.018) — it
instead splits off only the 18 highest-volume outliers (mean MADT 96k,
min 57.8k) from an undifferentiated 176-station remainder spanning all three
tiers. Those two raw clusters also have nearly identical weekly shapes (both
ordinary weekday-high/Sunday-low, just at different intensity) — confirming
that scale dominates raw-volume distance before weekly pattern gets a chance
to matter, which is exactly why shape-normalization is the right choice for
finding "similar-pattern" fallback siblings regardless of station size.

## 7. Final recommendation

- **Coverage:** cluster pooling is a real, if modest, win — +11 stations
  (+13% relative) at zero cost to the untouched individual-pool path.
- **Accuracy:** not yet proven better than the simplest same-functional-class
  baseline; don't present this as a strict improvement without the Phase 2
  work (full daily profiles instead of a 7-value reduction, and/or combining
  cluster membership with functional class rather than using it alone).
- **Before production use:** run the deferred stability checks (does the same
  station land in the same cluster across years/months?) and re-validate
  against `baseline_same_fc` specifically, since that's the bar to beat, not
  just "better than nothing."
- **Decision rule as it stands today:** individual pool first (unchanged);
  cluster fallback only as a coverage-of-last-resort when no simpler pooling
  rule is available — not as a general replacement for functional-class
  pooling.

## 8. Figure-by-figure interpretation

**`fig_missingness_distribution_apr2024.png`** — completeness across years for
April, n=273 stations. Strongly right-skewed with a small spike near 0 (8
stations with essentially no usable April history — likely newer stations)
and a large mass above 0.90 (142 of 273 stations sit in the top bin alone).
The 0.90 gate cuts through the rising slope, not a natural gap — a stricter or
looser threshold would move a meaningful number of stations in or out (this is
exactly the kind of decision the deferred 70/80/90% sensitivity sweep would
pressure-test).

**`fig_elbow_silhouette_apr2024.png`** — inertia decays smoothly with no sharp
elbow (typical for real, noisy data — WCSS alone doesn't give a crisp answer).
Silhouette peaks clearly but modestly at K=3 (0.406), dropping at K=4 (0.396)
and declining overall afterward with a minor local bump at K=9. K=3 is a real
local optimum, not an overwhelming one — consistent with the report's earlier
note that Calinski-Harabasz/Davies-Bouldin lean toward K=4–6.

**`fig_cluster_profiles_apr2024.png`** — the clearest evidence the clustering
is finding real structure, not noise. Three distinct weekly shapes: **Cluster
0** (n=126, majority) is flat-to-rising Mon–Fri then drops on Sat and drops
hard on Sun (~0.75×) — an ordinary commuter/business pattern. **Cluster 1**
(n=12, smallest) has the same weekday plateau but a much steeper weekend
cliff (Sat ~0.6×, Sun ~0.45×) — an extreme weekday-only pattern, consistent
with freight/industrial corridors that go nearly dead on weekends. **Cluster
2** (n=56) is comparatively flat all week with a Friday peak and only a mild
weekend dip (~0.95×) — a more recreational/general-purpose pattern where
weekend traffic doesn't collapse. This is a genuine three-way typology of
weekly shape.

**`fig_cluster_map_apr2024.png`** — clusters are geographically dispersed, not
regional. Cluster 0 (blue) and Cluster 2 (green) are both scattered statewide
with no obvious spatial separation, confirming §6's finding that clusters
aren't a proxy for urban/rural or region. Cluster 1 (orange, n=12) is the one
partial exception: several of its points cluster tightly near Savannah
(~-81.3, 32.1), Georgia's port/I-95 freight corridor — plausibly consistent
with the cluster's extreme weekday-only, weekend-dead shape, though n=12 is
too small to call this more than suggestive.

**`fig_pool_before_after_apr2024.png`** — both "before" and "after"
distributions are dominated by a huge spike of very small pools near zero
(most of the network never gets close to a usable pool, fallback or not), with
a long sparse tail out past 400. The visible shift is small but real: the
first bin drops from ~97 (individual) to ~89 (final) as the 11 rescued sites
move into the next bin or two (pool sizes in the 20–100 range) — consistent
with the actual rescued pool sizes recorded in `cluster_fallback_info_apr2024.csv`.

**`fig_coverage_before_after_apr2024.png`** — the single most important
"reality check" figure. `still_insufficient` (90) is now the *tallest* bar,
taller even than `individual` (84). The fallback helps, but even after it,
most of the originally-dropped network stays dropped — coverage moved from a
minority (45%) to a bare majority (51%) of eligible stations, not to "problem
solved."

**`fig_fallback_agreement_apr2024.png`** — true k* (x) vs. each method's k*
(y) across the 20 holdout sites × 6 mechanisms, with y=x for reference. No
method tracks the diagonal tightly — matching the moderate correlations
(0.73–0.82) in §5 — but the patterns differ: `cluster_fallback` (blue) tends
to sit at or slightly below the diagonal at low true k* (mild underestimate on
"easy" sites), while `baseline_all_pooled` (light green) shows the most
visible overestimation outliers (e.g. true k*=16 predicted as 28, the max
tested value) — the visual counterpart of its documented positive bias
(+2.10 days). This is the clearest visual evidence that the crude
"pool everything" baseline is the least trustworthy of the three, even though
its aggregate RMSE looked competitive.

## Files

- `clustering/output/profiles_apr2024.parquet`, `clustering/output/cluster_labels_apr2024.csv` — profiles + cluster assignments
- `clustering/output/cluster_fallback_info_apr2024.csv`, `clustering/output/cluster_fallback_kstar_apr2024.csv` — per-site method + k\*
- `clustering/output/coverage_before_after_apr2024.csv`, `clustering/output/validation_*_apr2024.csv` — the tables above
- `clustering/output/figures/*.png` — all figures referenced above
- `clustering/output/REPORT_apr2024.md` — auto-generated section-by-section dump (this file is the narrative version)
