# Feature Specification Document
Generated: 2026-04-10 01:48:57

---

## 1. station_feature_table.csv

One row per station (all stations in station_master_table, n=286).

| Column | Description | Units | Source |
|--------|-------------|-------|--------|
| station_id | Unique station identifier | — | station_master_table |
| cosit | GDOT COSIT sensor code | — | station_master_table |
| functional_class | FHWA functional classification | — | station_master_table |
| fc_urban_rural | Urban/Rural designation | — | station_master_table |
| county | County name | — | station_master_table |
| district | GDOT district number | — | station_master_table |
| latitude | Station latitude | decimal degrees | station_master_table |
| longitude | Station longitude | decimal degrees | station_master_table |
| n_sources | Number of counting sources at station | count | station_master_table |
| complete_months | Total complete months of historical data | months | station_master_table |
| median_daily_volume | Median total daily vehicle count | vehicles/day | station_daily_volume_summary |
| mean_daily_volume | Mean total daily vehicle count | vehicles/day | station_daily_volume_summary |
| weekday_median | Median volume on weekdays | vehicles/day | station_daily_volume_summary |
| weekend_median | Median volume on weekends | vehicles/day | station_daily_volume_summary |
| weekday_weekend_ratio | Ratio of weekday to weekend volume | dimensionless | station_daily_volume_summary |
| am_peak_hour | Hour of morning peak volume (0–23) | hour | station_daily_volume_summary |
| pm_peak_hour | Hour of afternoon peak volume (0–23) | hour | station_daily_volume_summary |
| pct_heavy | Fraction of heavy vehicles (F4–F15) | fraction [0,1] | station_daily_volume_summary |
| aadt_proxy_2023 | Annual average daily traffic proxy for 2023 (June-based estimate) | vehicles/year | aadt_trends_by_station |
| seasonal_amplitude | Max minus min seasonal index across months | dimensionless | seasonal_index_by_station |
| n_trusted_months_2024 | Number of months in 2024 with TRUSTED data quality | months | station_month_trustworthiness |
| pct_trusted_2024 | Fraction of 2024 months rated TRUSTED | fraction [0,1] | station_month_trustworthiness |
| n_anomaly_days_2024 | Total anomaly days detected in 2024 (trusted months) | days | station_month_trustworthiness |
| n_unexplained_2024 | Total unexplained anomaly days in 2024 | days | station_month_trustworthiness |
| n_months_total_2024 | Total months of 2024 data available | months | station_month_trustworthiness |
| is_trusted_2024 | True if station meets all trust criteria for 2024 modeling | boolean | derived |
| aadt_2024_estimate | Estimated 2024 AADT = median_daily_volume × 365 | vehicles/year | derived |

---

## 2. clean_hourly_2024_trusted.parquet

One row per (station, hour). Stations: 99, total rows: 818,645.
Covers calendar year 2024, only trusted stations, only hours with coverage >= 50%.

| Column | Description | Units |
|--------|-------------|-------|
| hour_start | UTC datetime floored to the hour | datetime |
| total_volume | Total vehicle count across all directions and 5-min bins | vehicles/hour |
| hourly_coverage | Mean detector coverage % across bins in the hour | percent [0,100] |
| n_bins | Number of 5-min bins with non-null count in the hour | count [0,12] |
| F1–F15 | Sum of vehicle class counts (FHWA classes 1–15) across directions | vehicles/hour |
| imputed | True if n_bins < 6 (hour has sparse data) | boolean |
| station_id | Station identifier | — |
| date | Calendar date | date |
| hour_of_day | Hour of the day (0–23) | hour |
| day_of_week | Day of week (0=Monday, 6=Sunday) | integer |
| month | Month of the year (1–12) | integer |
| is_weekday | True if Monday–Friday | boolean |

---

## 3. Aggregation Choices and Rationale

### 5-minute to Hourly
- All 5-minute bins within the same hour (floored) are aggregated.
- **Count** is summed across bins and directions: gives total vehicles per hour.
- **Coverage %** is averaged: represents mean detector availability.
- **Vehicle classes (F1–F15)** are summed.
- Hours with mean coverage < 50% are excluded to avoid unreliable totals.
- The `imputed` flag marks hours with < 6 non-null bins out of an expected 12
  (i.e., > 50% of 5-min intervals are missing).

### Rationale for Hourly Granularity
- Hourly is the standard resolution for traffic modeling and AADT derivation.
- Reduces raw 5-min noise while preserving diurnal patterns (am/pm peak).
- 100 stations × 366 days × 24 hours ≈ 878K rows — manageable in memory.

### AADT 2023 Proxy
- Derived from June mean daily volume × 365 in the trends analysis (Phase 3).
- June is used as it is the least seasonally biased month for Georgia.

### Seasonal Amplitude
- Computed as max(seasonal_index) − min(seasonal_index) per station.
- Higher values indicate stronger seasonal variation (useful for AADT correction).

---

## 4. Known Limitations and Caveats

1. **Direction aggregation**: All directions are summed. Stations with multiple
   lanes/directions are treated as a combined total — no directional split.

2. **Coverage threshold**: The 50% coverage cutoff is conservative. Some hours
   near the threshold may still have unreliable counts.

3. **Imputation flag**: The `imputed=True` flag does NOT impute values — it only
   flags potentially unreliable hours for downstream filtering.

4. **AADT 2023 proxy**: Derived from a single month (June); less accurate for
   stations with strong seasonal patterns (high seasonal_amplitude).

5. **Station cap**: Task 2 processes up to 100 trusted stations. Remaining
   trusted stations are not included in the hourly parquet.

6. **Multi-source stations**: Stations with n_sources > 1 may double-count
   vehicles if multiple sensors cover the same road segment.

7. **2024 coverage**: Data availability varies by station. Some stations may
   have large gaps (holidays, sensor outages) not captured by the trust tier.

8. **Class columns (F1–F15)**: Some stations do not record vehicle classification;
   these columns will show 0 or NaN rather than being absent.
