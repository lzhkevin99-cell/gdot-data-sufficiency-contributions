## Objective
Build clean, analysis-ready datasets and feature tables from trusted GDOT 2024
traffic count station data, supporting downstream modeling and AADT estimation.

## Methods

### Station Selection (Task 1)
- Loaded station_month_trustworthiness.csv (20,600 rows across all years/months).
- Filtered to year=2024 and trust_tier='TRUSTED'; required ≥6 trusted months.
- Intersected with trusted_station_list.csv (243 stations) and
  station_master_table filtered to in_5min_2024=True (233 stations).
- Final trusted set: **207 stations** with raw data files on disk: **100 stations** (capped at 100).

### Hourly Dataset (Task 2)
- For each trusted station, read raw 5-min CSV (chunked at 50k rows).
- Aggregated all 5-min bins within each clock hour: summed Count and F1–F15,
  averaged Coverage %, counted non-null bins (n_bins).
- Applied coverage filter: excluded hours with mean coverage < 50%.
- Flagged hours with n_bins < 6 as imputed=True.
- Added temporal features: date, hour_of_day, day_of_week, month, is_weekday.

### Feature Table (Task 3)
- Started from full station_master_table (286 stations).
- Left-merged: daily volume summary, AADT 2023 proxy, seasonal amplitude,
  and 2024 trustworthiness statistics.
- Derived: is_trusted_2024 flag, aadt_2024_estimate = median_daily_volume × 365.

### Aggregation Comparison (Task 4)
- Selected 5 example trusted stations.
- For each: loaded raw 5-min data, aggregated to hourly and daily.
- Plotted 3×5 subplot grid for June 3–9, 2024 reference week.

## Key Findings

**Station coverage:**
- Stations in master table: 286
- Stations with ≥6 trusted 2024 months: 211
- Stations meeting all trust criteria with data on disk: 100

**Hourly dataset:**
- Stations processed: 99
- Total hourly records: 818,645
- Columns: 26
    - Mean hourly coverage: 100.0%
    - Min hourly coverage: 50.0%
    - Coverage threshold applied: >=50%
    - Imputed-flagged hours: 1.7% of retained hours
    - Median hourly volume: 580 vehicles
    - Max hourly volume: 17822 vehicles

**Feature table:**
- Rows (stations): 286
- Columns (features): 27
- Trusted stations flagged: 100

## Tables/Plots Created

| File | Description |
|------|-------------|
| `clean_hourly_2024_trusted.parquet` | 818,645 hourly records, 26 cols, 99 stations |
| `clean_hourly_2024_trusted_sample.csv` | First 10,000 rows of hourly parquet |
| `station_feature_table.csv` | 286 stations × 27 features |
| `fig_aggregation_comparison.png` | 3×5 subplot: 5-min / hourly / daily for 5 stations |
| `feature_spec.md` | Column-level documentation for all outputs |
| `feature_pipeline_report.md` | This report |

## Risks/Caveats

1. **Direction summing**: No directional split; all lanes summed. Multi-lane
   stations may not be comparable to single-lane stations on a per-lane basis.
2. **Coverage threshold**: 50% cutoff retains some noisy hours. Models should
   use `imputed` flag for additional filtering.
3. **Station cap**: Only 100 of 207 trusted stations processed for
   hourly data due to the 100-station cap. Feature table includes all 286 stations.
4. **AADT 2023 proxy**: June-based estimate; accuracy degrades for stations
   with high seasonal amplitude (>0.4).
5. **Multi-source double-counting**: Stations with n_sources > 1 aggregate
   across sensors; may over-count if sensors overlap spatially.

## Recommended Next Steps

1. **AADT modeling**: Use station_feature_table.csv with functional_class,
   seasonal_amplitude, and aadt_proxy_2023 as predictors for AADT estimation.
2. **Imputation**: For the 100 trusted stations, build a gap-filling
   model using neighboring trusted stations (spatial kriging or k-NN).
3. **Directional analysis**: Re-run hourly aggregation with direction as a
   grouping variable for travel demand modeling.
4. **Seasonal correction**: Apply seasonal_index to aadt_2024_estimate to
   derive bias-corrected AADT for months with high seasonal amplitude.
5. **Remove 100-station cap**: Process all 207 trusted stations for
   full-population hourly dataset (requires ~1656GB RAM estimate).
6. **Validation**: Cross-validate aadt_2024_estimate against GDOT official AADT
   counts where available.
