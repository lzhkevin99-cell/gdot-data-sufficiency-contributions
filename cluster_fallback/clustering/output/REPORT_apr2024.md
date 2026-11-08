# Cluster-Enhanced Reference-Pool Fallback -- MVP Report (apr2024)

*This is the raw, auto-generated per-run section dump. See `../REPORT.md` for the curated narrative version of these results.*

## 1. Practical problem

The existing conformal data-sufficiency pipeline requires each target station-month to have a reference pool of >= `MIN_POOL_SIZE=19` correlated companion-months. For this target month, a large share of eligible stations fail this bar and are silently dropped with no record of why. This MVP adds a traffic-pattern-cluster-based fallback to rescue some of them.

## 2. Existing pipeline and reference-pool limitation

See `coverage_before_after_apr2024.csv` below (Section 12) for the exact counts. `run_multi_site.run_site()` returns `None` and increments a fail counter with no persisted reason when `pool_size < MIN_POOL_SIZE` (run_multi_site.py:217-220,396-399).

## 3-4. Data used and profile construction

Profiles: 7-element day-of-week mean vector (raw + shape-normalized), averaged across all available years of the target month in `complete_months_all.parquet`. 265 stations have >=1 complete target-month; 194 pass the profile-completeness gate (`PROFILE_COMPLETENESS_MIN=0.9`, measured from the daily inventory, not `complete_months_all.parquet`).

## 5. Missing-data treatment

See `missingness_by_station_apr2024.csv`/`missingness_by_year_apr2024.csv` and `fig_missingness_distribution.png`. Direction rows are summed (not `.max()`-deduped) so bidirectional stations aren't undercounted.

## 6-7. Clustering method and K selection

KMeans on the standardized shape-normalized profile. K sweep (`kmeans_sweep_apr2024.csv`) evaluated K=2..12; selected K=3 by argmax silhouette (silhouette=0.406). Calinski-Harabasz/Davies-Bouldin favor a nearby K (see raw sweep table) -- criteria disagree somewhat; K=3 was kept for parsimony, per the documented MVP rule. **[REQUIRES PHASE 2]** for a full elbow/CH/DB agreement study.
Cluster sizes: {0: 126, 1: 12, 2: 56}.

## 8. Cluster stability

**[REQUIRES PHASE 2]** -- bootstrap/subsampling stability, cross-year/cross-month ARI, and raw-vs-shape agreement were not run in this MVP pass. Only a single seeded KMeans fit (seed=42) was evaluated.

## 9. Cluster interpretation

**cluster_x_fc**:

```
fc_label    1: Interstate  2: Other Freeways / Expressways  3: Other Principal Arterial  4: Minor Arterial  5: Major Collector  6: Minor Collector  7: Local Access
cluster_id                                                                                                                                                         
0                      30                                9                           39                 28                  16                   1                1
1                       1                                2                            3                  2                   4                   0                0
2                      33                                1                           10                  5                   5                   0                1
```

**cluster_x_ur**:

```
urban_rural   R   U
cluster_id         
0            28  96
1             1  11
2            23  32
```

**cluster_x_volume_tier**:

```
volume_tier  Low (<5k)  Medium (5-15k)  High (>15k)
cluster_id                                         
0                   45              40           41
1                    6               6            0
2                   16              10           30
```

Clusters are not a simple re-derivation of functional class, urban/rural, or volume tier -- each cluster contains a mix of all three, suggesting the shape-based grouping captures a genuinely different axis of variation (weekday/weekend pattern) than the paper's existing volume-tier stratification.

## 10. Integration with the existing pipeline

`clustering/fallback.py::run_station_month()` -- individual pool first (delegates to the same `modules/` primitives `run_multi_site.run_site()` calls); cluster-pooled fallback only when the individual pool is insufficient. Zero edits to `run_multi_site.py`. Leakage guard: asserts the augmented pool never contains the target's own row.

## 11. Validation of cluster-enhanced K*

Holdout comparison against ground truth (`validation_overall_apr2024.csv`):


```
             method     n      mae     rmse      bias     corr
baseline_all_pooled 108.0 3.175926 4.890467  2.101852 0.787159
   baseline_same_fc  96.0 2.906250 4.297528 -1.260417 0.817705
   cluster_fallback 100.0 3.480000 4.845617  0.680000 0.735064
```

By cluster (`validation_by_cluster_apr2024.csv`):

```
             method  cluster_id    n      mae     rmse      bias     corr
baseline_all_pooled         0.0 96.0 3.510417 5.175060  2.427083 0.755553
baseline_all_pooled         1.0  6.0 0.666667 1.154701 -0.666667 0.965363
   baseline_same_fc         0.0 90.0 3.033333 4.413364 -1.277778 0.815916
   baseline_same_fc         1.0  6.0 1.000000 1.825742 -1.000000 0.911465
   cluster_fallback         0.0 94.0 3.627660 4.979746  0.797872 0.734653
   cluster_fallback         1.0  6.0 1.166667 1.683251 -1.166667 0.988799
```

By functional class (`validation_by_fc_apr2024.csv`):

```
             method  fc_code    n      mae     rmse      bias     corr
baseline_all_pooled        2 18.0 2.500000 3.880149 -2.500000 0.922979
baseline_all_pooled        3 50.0 2.160000 4.345112  1.640000 0.746894
baseline_all_pooled        4 36.0 5.277778 6.164414  5.277778 0.846881
baseline_all_pooled        5  4.0 0.000000 0.000000  0.000000      NaN
   baseline_same_fc        3 54.0 2.925926 4.566383 -1.148148 0.746916
   baseline_same_fc        4 36.0 2.444444 3.543382 -0.722222 0.889739
   baseline_same_fc        5  6.0 5.500000 5.700877 -5.500000      NaN
   cluster_fallback        2 12.0 6.666667 7.129750 -6.666667 0.925899
   cluster_fallback        3 54.0 2.129630 3.613247 -0.092593 0.839465
   cluster_fallback        4 34.0 4.500000 5.512019  4.500000 0.863005
```

## 12. Coverage improvement

```
            method  count
        individual     84
  cluster_fallback     11
still_insufficient     90
    no_target_data      0
        n_eligible    185
    residual_check      0
```

## 13. Sensitivity analyses

**[REQUIRES PHASE 2]** -- the 8-dimension sensitivity matrix, completeness-threshold sweep (70/80/90%), and algorithm comparison (Ward/GMM/k-medoids/DBSCAN) were not run in this MVP pass. A single default was fixed and documented for each new parameter instead (see plan).

## 14. Limitations

- Profiles are a 7-value day-of-week reduction, not full daily/realigned vectors.
- Single target month only (no cross-month clustering stability check).
- No `lanes`/`district` metadata exists in `site_metadata.parquet` -- not usable for crosstabs, here or in any future phase.
- K selected by a single rule (argmax silhouette); other criteria disagree slightly.
- Holdout validation uses a synthetic pool-truncation design, not naturally-occurring insufficient sites with known ground truth (none exist by definition).

## 15. Final recommendation

Explicit answers to the recommendation questions the MVP can support are in the chat summary accompanying this report; questions requiring Phase 2 work (algorithm choice beyond KMeans, stability across years/months, sensitivity matrix) are tagged `[REQUIRES PHASE 2]` above rather than answered speculatively.
