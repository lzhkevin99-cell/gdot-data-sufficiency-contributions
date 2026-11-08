## Objective

Characterize baseline 2024 traffic behavior (volume, temporal patterns, vehicle mix, and station archetypes) across a stratified sample of GDOT 5-minute count stations. This is Phase 2A of the GDOT EDA workflow.

## Methods

- **Input data**: 2024 CCS 5-minute count CSVs from CCS_5Min_2024; station master table and missingness scorecard from prior phases.
- **Eligibility filter**: `in_5min_2024 == True` AND `pct_complete > 0.7` → 208 eligible stations.
- **Stratified sample**: 100 stations sampled proportionally across functional-class × urban/rural strata, preferring stations with highest completeness.
- **Coverage filter**: Only 5-min bins with Coverage % ≥ 50% were used to avoid treating outages as zeros.
- **Direction aggregation**: Multiple direction rows per timestamp were summed to get station-level totals.
- **Profiles computed**: Daily volume summary, hourly (weekday/weekend), day-of-week, and monthly.
- **Vehicle mix**: F1–F15 bins normalized to fraction of total classified volume.
- **Archetypes**: k-means (k=4) clustering on weekday/weekend ratio, AM/PM peak hour, pct-heavy-vehicle, and normalized median daily volume; clusters labeled by dominant characteristic.

## Key Findings

- **Stations processed**: 100 (skipped 0 due to missing/corrupt files).
- **Median daily volume** across all sampled stations: 22,830 counts/day.
- **Mean daily volume** across all sampled stations: 45,223 counts/day.
- **Weekday/weekend ratio**: median = 1.25 — indicating most stations carry more traffic on weekdays.
- **AM peak hour** (most common across stations): 7:00.
- **PM peak hour** (most common): 17:00.

### Volume by Functional Class

| functional_class                |   n_stations |   median_daily_volume |   weekday_weekend_ratio |
|:--------------------------------|-------------:|----------------------:|------------------------:|
| 1: Interstate                   |           38 |              51717.5  |                 1.07595 |
| 2: Other Freeways / Expressways |            6 |             110252    |                 1.2199  |
| 3: Other Principal Arterial     |           26 |              19373.5  |                 1.34862 |
| 4: Minor Arterial               |           18 |              12076.2  |                 1.35467 |
| 5: Major Collector              |           12 |               1894.25 |                 1.43788 |

### Archetype Distribution

- **Mixed**: 77 stations
- **Freight/Arterial**: 1 stations

## Tables/Plots Created

| File | Description |
|------|-------------|
| `station_daily_volume_summary.csv` | Per-station daily volume statistics and peak hours |
| `station_hourly_profiles.csv` | Per-station hourly mean counts (weekday/weekend) |
| `station_dow_profiles.csv` | Per-station day-of-week mean daily volumes |
| `station_monthly_profiles.csv` | Per-station monthly mean daily volumes |
| `station_archetypes.csv` | Station archetype labels and clustering features |
| `fig_hourly_profile_by_fc.png` | Normalized weekday hourly profiles by functional class |
| `fig_dow_profile_by_fc.png` | Day-of-week profiles by functional class |
| `fig_monthly_profile.png` | Monthly mean daily volume across all stations |
| `fig_weekday_weekend_ratio.png` | Distribution of weekday/weekend ratio by FC |
| `fig_vehicle_mix_by_fc.png` | F1–F15 vehicle mix stacked bar by FC |
| `fig_am_pm_peak_hour_distribution.png` | Histograms of AM and PM peak hours |
| `fig_archetype_summary.png` | 2×2 average weekday hourly profiles by archetype |

## Risks/Caveats

- Analysis uses only `data-1.csv` per station; additional data files (`data-2.csv`, `data-3.csv`) are excluded.
- Coverage % filter (≥50%) may still include periods with partial lane failures.
- F1–F15 fractions are only meaningful when classified volume > 0; stations with poor classifier coverage may show skewed mixes.
- k-means archetype labels are heuristic; boundary cases may be mis-assigned.
- Stratified sampling favors completeness; less reliable stations are underrepresented.
- 0 stations were skipped due to file read errors or empty data after filtering.

## Recommended Next Steps

- **Phase 2B (speed profile agent)**: Analyze speed bin distributions alongside volume.
- **Outlier investigation**: Examine stations with extreme weekday/weekend ratios (>3 or <0.5).
- **Seasonal decomposition**: Fit STL or similar models to monthly profiles to separate trend from seasonality.
- **Archetype validation**: Cross-reference archetypes with land-use/AADT data for external validation.
- **Lane-level analysis**: Incorporate direction-split data for directional peak analysis.
- **Missing data imputation**: Use archetype profiles to impute gaps in incomplete stations.