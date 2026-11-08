## Objective
Identify corridor relationships among GDOT ATR stations by computing pairwise
Pearson correlations of daily traffic volumes, applying hierarchical clustering
to group stations with similar temporal behavior, computing geographic and
behavioral proximity, and ranking reference station candidates for downstream
imputation and bias-correction work.

## Methods
- **Input stations**: 230 stations (in_5min_2024=True, n_sources≥2)
  from station_master_table.csv.
- **Daily volume matrix**: Built by reading raw 5-min data-1.csv files for the
  top 80 stations (ranked by pct_complete). For each station,
  5-min records with Coverage % ≥ 50 were summed to daily totals; only 2024
  dates were retained.
  - Matrix dimensions: 366 dates × 80 stations.
- **Correlation**: Pairwise Pearson r computed with min_periods=180
  overlapping non-null days.
- **Clustering**: Scipy hierarchical linkage ('average' method) on distance = 1−r;
  flat clusters extracted at distance threshold 0.15 (equivalent to r > 0.85).
- **Behavioral neighbors**: A neighbor pair (within 50.0 km AND r > 0.7).
- **Reference candidates**: Must satisfy all 5 criteria (pct_complete ≥ 0.85,
  complete_months ≥ 10, ≥ 2 behavioral neighbors, n_sources = 3, not singleton).

## Key Findings
- **Valid station pairs** (≥180 overlap days): 2,848 pairs from
  80 stations.
- **Pairwise r**: mean = 0.573, median = 0.636,
  range [-0.240, 0.993].
- **High-correlation pairs** (r > 0.85): 411 pairs
  (14.4% of all valid pairs).
- **Clusters found**: 44 total cluster IDs; 7 multi-station
  corridor clusters; 37 singleton stations.
- **Behavioral neighbor pairs** (r > 0.7, dist < 50.0 km):
  211 pairs.
- **Reference station candidates**: 27 stations passed all 5 criteria.

## Tables/Plots Created
| File | Description |
|------|-------------|
| pairwise_correlation_matrix.csv | 80×80 Pearson r matrix |
| corridor_cluster_assignments.csv | Cluster IDs + intra-cluster stats for 76 stations |
| behavioral_neighbor_table.csv | 705 station-neighbor rows with r and distance |
| reference_station_candidates.csv | 27 ranked reference candidates |
| fig_correlation_distribution.png | Histogram of pairwise r values |
| fig_correlation_heatmap.png | Clustered heatmap (reordered by cluster) |
| fig_geographic_clusters_map.png | Lat/lon scatter colored by cluster ID |

## Risks / Caveats
1. **Subset only**: Correlation matrix is built from the top 80 stations
   by data completeness; stations ranked 81+ are excluded and may form additional
   corridor groups not captured here.
2. **Min-overlap threshold**: Requiring ≥180 overlapping non-null days
   between pairs can exclude station pairs where one station had a long outage,
   even if their overlapping period shows high correlation.
3. **Data-1.csv only**: Only the first data source tier (data-1.csv) is used for
   volume; stations appearing solely in data-2 or data-3 are not included.
4. **2024 calendar only**: Seasonal/annual correlation patterns may differ for
   stations that were active in 2024 only during specific months.
5. **No road-network topology**: "Corridor" clusters are purely behavioral (temporal
   volume co-movement); they do not guarantee stations are on the same roadway.

## Recommended Next Steps
1. **Phase 3B integration**: Merge seasonal pattern results with corridor cluster IDs
   to identify stations with both high spatial proximity and consistent seasonal shape.
2. **Expand to full station set**: After Phase 3B, re-run correlation with all
   in_5min_2024 stations using a lower min_periods threshold (e.g. 90 days) to
   capture shorter-operation stations.
3. **Network topology overlay**: Cross-reference cluster membership with GDOT route
   IDs or GIS road segments to confirm behavioral clusters align with physical corridors.
4. **Reference station validation**: For the 27 candidates, compare
   their hourly profiles (from station_hourly_profiles.csv) to verify they represent
   typical diurnal shapes for their functional class.
5. **Imputation design**: Use behavioral neighbors (r > 0.7, dist < 50.0 km)
   as donor stations for gap-filling; reference station candidates are the first-choice
   donors.
