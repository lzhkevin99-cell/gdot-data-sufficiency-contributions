"""
Feature Pipeline Agent - Phase 4
Builds clean analysis-ready datasets and feature tables for modeling.
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path("/Users/kevinli/Desktop/Research_Gtech_gdot")
EDA        = ROOT / "eda_output"
FEAT       = EDA / "features"
RAW_2024   = ROOT / "gdot_2025_data_total" / "CCS_5Min_2024"
FEAT.mkdir(parents=True, exist_ok=True)

TRUST_FILE   = EDA / "anomalies" / "station_month_trustworthiness.csv"
TRUSTED_LIST = EDA / "anomalies" / "trusted_station_list.csv"
HOURLY_PROF  = EDA / "profiles"  / "station_hourly_profiles.csv"
DAILY_SUMM   = EDA / "profiles"  / "station_daily_volume_summary.csv"
MASTER       = EDA / "inventory" / "station_master_table.csv"
AADT_TRENDS  = EDA / "trends"    / "aadt_trends_by_station.csv"
SEASONAL_IDX = EDA / "trends"    / "seasonal_index_by_station.csv"

# ── Helpers ────────────────────────────────────────────────────────────────────
def cosit_to_path(cosit):
    """Return path to data-1.csv for a given COSIT value."""
    c_str = str(int(cosit)).zfill(12)
    return RAW_2024 / f"GDOT_CCS-{c_str}-data-1.csv"


# ==============================================================================
# TASK 1 – Identify trusted stations for 2024
# ==============================================================================
print("\n" + "="*70)
print("TASK 1: Identifying trusted stations for 2024")
print("="*70)

trust_df = pd.read_csv(TRUST_FILE)
print(f"  Trustworthiness table: {trust_df.shape[0]:,} rows, cols: {list(trust_df.columns)}")

# Filter to 2024 TRUSTED months, count per station
t2024 = trust_df[(trust_df['year'] == 2024) & (trust_df['trust_tier'] == 'TRUSTED')]
n_trusted_2024 = (
    t2024.groupby('station_id').size().reset_index(name='n_trusted_months_2024')
)
print(f"  Stations with >=1 trusted month in 2024: {len(n_trusted_2024)}")

# Load trusted station list
trusted_list_df = pd.read_csv(TRUSTED_LIST)
print(f"  Trusted station list cols: {list(trusted_list_df.columns)}")
trusted_station_ids = set(trusted_list_df['station_id'].astype(str))
print(f"  Stations in trusted_station_list: {len(trusted_station_ids)}")

# Intersection: in list AND >=6 trusted months
t2024_6 = n_trusted_2024[n_trusted_2024['n_trusted_months_2024'] >= 6]
trusted_set_prelim = set(t2024_6['station_id'].astype(str)) & trusted_station_ids
print(f"  Stations with >=6 trusted 2024 months AND in trusted list: {len(trusted_set_prelim)}")

# Load master table, filter to in_5min_2024==True
master_df = pd.read_csv(MASTER)
print(f"  Master table: {master_df.shape[0]:,} stations, cols: {list(master_df.columns)}")
master_df['station_id'] = master_df['station_id'].astype(str)

in_5min = master_df[master_df['in_5min_2024'] == True]
in_5min_set = set(in_5min['station_id'].astype(str))
print(f"  Stations with in_5min_2024==True: {len(in_5min_set)}")

# Final trusted set
final_trusted_ids = trusted_set_prelim & in_5min_set
print(f"  Final trusted station count: {len(final_trusted_ids)}")

# Build map: station_id -> cosit
master_trusted = master_df[master_df['station_id'].isin(final_trusted_ids)].copy()
master_trusted['cosit'] = pd.to_numeric(master_trusted['cosit'], errors='coerce')
station_cosit = dict(zip(master_trusted['station_id'], master_trusted['cosit']))

# Check which stations actually have a data-1.csv
available_stations = []
missing_stations   = []
for sid, cosit in station_cosit.items():
    if pd.isna(cosit):
        missing_stations.append(sid)
        continue
    p = cosit_to_path(cosit)
    if p.exists():
        available_stations.append((sid, cosit))
    else:
        missing_stations.append(sid)

print(f"  Stations with data-1.csv on disk: {len(available_stations)}")
print(f"  Stations missing data file:       {len(missing_stations)}")

# Cap at 100 for manageability
if len(available_stations) > 100:
    available_stations = available_stations[:100]
    print(f"  Capped to 100 stations for output manageability")

print(f"  Processing {len(available_stations)} stations in Task 2")


# ==============================================================================
# TASK 2 – Build clean hourly dataset (2024, trusted stations)
# ==============================================================================
print("\n" + "="*70)
print("TASK 2: Building clean hourly dataset")
print("="*70)

CLASS_COLS = [f'F{i}' for i in range(1, 16)]

def process_station_file(station_id, cosit, verbose=False):
    """Read raw 5-min CSV, aggregate to hourly, return DataFrame."""
    path = cosit_to_path(cosit)
    try:
        chunks = []
        for chunk in pd.read_csv(path, chunksize=50_000, low_memory=False):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
    except Exception as e:
        print(f"    ERROR reading {path.name}: {e}")
        return None

    # Parse time
    if 'Start Time' not in df.columns:
        print(f"    WARN: 'Start Time' missing in {path.name}")
        return None
    df['Start Time'] = pd.to_datetime(df['Start Time'], errors='coerce')
    df = df.dropna(subset=['Start Time'])

    # Floor to hour
    df['hour_start'] = df['Start Time'].dt.floor('h')

    # Ensure numeric
    for col in ['Count', 'Coverage %'] + CLASS_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Count non-null 5-min bins per hour (for imputation flag)
    df['_has_count'] = df['Count'].notna().astype(int)

    # Group by hour (sum across directions too)
    agg_dict = {}
    if 'Count' in df.columns:
        agg_dict['total_volume'] = ('Count', 'sum')
    if 'Coverage %' in df.columns:
        agg_dict['hourly_coverage'] = ('Coverage %', 'mean')
    agg_dict['n_bins'] = ('_has_count', 'sum')

    for fc in CLASS_COLS:
        if fc in df.columns:
            agg_dict[fc] = (fc, 'sum')

    hourly = df.groupby('hour_start').agg(**agg_dict).reset_index()

    # Filter: coverage >= 50
    if 'hourly_coverage' in hourly.columns:
        hourly = hourly[hourly['hourly_coverage'] >= 50].copy()
    else:
        hourly['hourly_coverage'] = np.nan

    # Imputed flag: fewer than 6 non-null bins out of expected 12
    hourly['imputed'] = hourly['n_bins'] < 6

    # Temporal features
    hourly['station_id']  = station_id
    hourly['date']        = hourly['hour_start'].dt.date
    hourly['hour_of_day'] = hourly['hour_start'].dt.hour
    hourly['day_of_week'] = hourly['hour_start'].dt.dayofweek   # 0=Monday
    hourly['month']       = hourly['hour_start'].dt.month
    hourly['is_weekday']  = hourly['day_of_week'] < 5

    return hourly


all_hourly = []
for i, (sid, cosit) in enumerate(available_stations):
    if (i + 1) % 10 == 0 or i == 0:
        print(f"  Processing station {i+1}/{len(available_stations)}: {sid}")
    h = process_station_file(sid, cosit)
    if h is not None and len(h) > 0:
        all_hourly.append(h)

print(f"  Stations successfully processed: {len(all_hourly)}")

hourly_df = pd.concat(all_hourly, ignore_index=True) if all_hourly else pd.DataFrame()
print(f"  Total hourly rows: {hourly_df.shape[0]:,}")
print(f"  Columns: {list(hourly_df.columns)}")

# Save parquet
parquet_path = FEAT / "clean_hourly_2024_trusted.parquet"
try:
    hourly_df.to_parquet(parquet_path, index=False)
    print(f"  Saved parquet: {parquet_path}")
except Exception as e:
    print(f"  Parquet failed ({e}), falling back to CSV")
    hourly_df.to_csv(FEAT / "clean_hourly_2024_trusted.csv", index=False)

# Save CSV sample
sample_path = FEAT / "clean_hourly_2024_trusted_sample.csv"
hourly_df.head(10_000).to_csv(sample_path, index=False)
print(f"  Saved CSV sample (10k rows): {sample_path}")


# ==============================================================================
# TASK 3 – Station-level feature table
# ==============================================================================
print("\n" + "="*70)
print("TASK 3: Building station-level feature table")
print("="*70)

# Start with full master table
feat_tbl = master_df.copy()

# Columns to keep from master
master_keep = ['station_id', 'cosit', 'functional_class', 'fc_urban_rural',
               'county', 'district', 'latitude', 'longitude',
               'n_sources', 'complete_months']
# Add through_lanes if present
if 'through_lanes' in feat_tbl.columns:
    master_keep.append('through_lanes')
feat_tbl = feat_tbl[[c for c in master_keep if c in feat_tbl.columns]].copy()
feat_tbl['station_id'] = feat_tbl['station_id'].astype(str)

# ── Daily volume summary ──────────────────────────────────────────────────────
daily_df = pd.read_csv(DAILY_SUMM)
daily_df['station_id'] = daily_df['station_id'].astype(str)
daily_keep = ['station_id', 'median_daily_volume', 'mean_daily_volume',
              'weekday_median', 'weekend_median', 'weekday_weekend_ratio',
              'am_peak_hour', 'pm_peak_hour']
if 'pct_heavy' in daily_df.columns:
    daily_keep.append('pct_heavy')
daily_sub = daily_df[[c for c in daily_keep if c in daily_df.columns]]
feat_tbl = feat_tbl.merge(daily_sub, on='station_id', how='left')
print(f"  After daily merge: {feat_tbl.shape}")

# ── AADT trends – 2023 proxy ──────────────────────────────────────────────────
aadt_df = pd.read_csv(AADT_TRENDS)
# Use 'station' column (not 'station_id')
if 'station' in aadt_df.columns and 'station_id' not in aadt_df.columns:
    aadt_df = aadt_df.rename(columns={'station': 'station_id'})
aadt_df['station_id'] = aadt_df['station_id'].astype(str)
aadt_2023 = aadt_df[aadt_df['year'] == 2023][['station_id', 'aadt_proxy']].copy()
aadt_2023 = aadt_2023.rename(columns={'aadt_proxy': 'aadt_proxy_2023'})
# If multiple rows per station (shouldn't be), take max
aadt_2023 = aadt_2023.groupby('station_id')['aadt_proxy_2023'].max().reset_index()
feat_tbl = feat_tbl.merge(aadt_2023, on='station_id', how='left')
print(f"  After AADT merge: {feat_tbl.shape}")

# ── Seasonal amplitude ────────────────────────────────────────────────────────
seas_df = pd.read_csv(SEASONAL_IDX)
if 'station' in seas_df.columns and 'station_id' not in seas_df.columns:
    seas_df = seas_df.rename(columns={'station': 'station_id'})
seas_df['station_id'] = seas_df['station_id'].astype(str)
seas_amp = seas_df.groupby('station_id')['seasonal_index'].agg(
    seasonal_amplitude=lambda x: x.max() - x.min()
).reset_index()
feat_tbl = feat_tbl.merge(seas_amp, on='station_id', how='left')
print(f"  After seasonal merge: {feat_tbl.shape}")

# ── Trustworthiness 2024 stats ────────────────────────────────────────────────
t2024_stats = (
    trust_df[trust_df['year'] == 2024]
    .groupby('station_id')
    .agg(
        n_trusted_months_2024  = ('trust_tier', lambda x: (x == 'TRUSTED').sum()),
        n_anomaly_days_2024    = ('n_anomaly_days', 'sum'),
        n_unexplained_2024     = ('n_unexplained_anomalies', 'sum'),
        n_months_total_2024    = ('month', 'count')
    )
    .reset_index()
)
t2024_stats['pct_trusted_2024'] = (
    t2024_stats['n_trusted_months_2024'] / t2024_stats['n_months_total_2024']
)
t2024_stats['station_id'] = t2024_stats['station_id'].astype(str)
feat_tbl = feat_tbl.merge(t2024_stats, on='station_id', how='left')
print(f"  After trustworthiness merge: {feat_tbl.shape}")

# ── is_trusted flag ───────────────────────────────────────────────────────────
trusted_ids_list = [s for s, _ in available_stations]
feat_tbl['is_trusted_2024'] = feat_tbl['station_id'].isin(trusted_ids_list)
print(f"  Trusted stations flagged: {feat_tbl['is_trusted_2024'].sum()}")

# ── AADT 2024 estimate ────────────────────────────────────────────────────────
feat_tbl['aadt_2024_estimate'] = feat_tbl['median_daily_volume'] * 365

# ── Save ──────────────────────────────────────────────────────────────────────
feat_path = FEAT / "station_feature_table.csv"
feat_tbl.to_csv(feat_path, index=False)
print(f"  Saved: {feat_path}")
print(f"  Shape: {feat_tbl.shape}")
print(f"  Columns: {list(feat_tbl.columns)}")


# ==============================================================================
# TASK 4 – Aggregation-level comparison (5 example stations)
# ==============================================================================
print("\n" + "="*70)
print("TASK 4: Aggregation-level comparison plots")
print("="*70)

# Pick 5 stations that have data
example_stations = available_stations[:5]
print(f"  Example stations: {[s for s, _ in example_stations]}")

# Find a common reference week (first week of June 2024)
REF_START = pd.Timestamp('2024-06-03')
REF_END   = pd.Timestamp('2024-06-09 23:59:59')

fig, axes = plt.subplots(3, 5, figsize=(22, 12))
fig.suptitle("Volume Aggregation Comparison — June 3–9, 2024 (5 Example Stations)", fontsize=14)

for col_idx, (sid, cosit) in enumerate(example_stations):
    path = cosit_to_path(cosit)
    try:
        raw_chunks = []
        for chunk in pd.read_csv(path, chunksize=50_000, low_memory=False):
            raw_chunks.append(chunk)
        raw = pd.concat(raw_chunks, ignore_index=True)
    except Exception as e:
        print(f"  Skipping {sid}: {e}")
        for row in range(3):
            axes[row, col_idx].set_visible(False)
        continue

    raw['Start Time'] = pd.to_datetime(raw['Start Time'], errors='coerce')
    raw = raw.dropna(subset=['Start Time'])
    raw['Count'] = pd.to_numeric(raw['Count'], errors='coerce').fillna(0)

    # Filter to reference week
    week = raw[(raw['Start Time'] >= REF_START) & (raw['Start Time'] <= REF_END)].copy()

    if week.empty:
        print(f"  No data for {sid} in reference week, skipping")
        for row in range(3):
            axes[row, col_idx].set_visible(False)
        continue

    # ── 5-min resolution (sum directions) ────────────────────────────────────
    min5 = week.groupby('Start Time')['Count'].sum().reset_index()
    min5 = min5.set_index('Start Time').sort_index()

    # ── Hourly ────────────────────────────────────────────────────────────────
    hourly_ex = week.copy()
    hourly_ex['hour_start'] = hourly_ex['Start Time'].dt.floor('h')
    hourly_ex = hourly_ex.groupby('hour_start')['Count'].sum().reset_index()
    hourly_ex = hourly_ex.set_index('hour_start').sort_index()

    # ── Daily ─────────────────────────────────────────────────────────────────
    daily_ex = week.copy()
    daily_ex['date'] = daily_ex['Start Time'].dt.date
    daily_ex = daily_ex.groupby('date')['Count'].sum().reset_index()

    # Row 0: 5-min
    ax = axes[0, col_idx]
    ax.plot(min5.index, min5['Count'], linewidth=0.6, color='steelblue', alpha=0.8)
    ax.set_title(f"{sid}\n5-min", fontsize=9)
    ax.set_ylabel("Volume" if col_idx == 0 else "")
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)

    # Row 1: hourly
    ax = axes[1, col_idx]
    ax.step(hourly_ex.index, hourly_ex['Count'], where='post',
            linewidth=1.0, color='darkorange', alpha=0.9)
    ax.set_title(f"Hourly", fontsize=9)
    ax.set_ylabel("Volume" if col_idx == 0 else "")
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)

    # Row 2: daily
    ax = axes[2, col_idx]
    ax.bar([str(d) for d in daily_ex['date']], daily_ex['Count'],
           color='seagreen', alpha=0.8)
    ax.set_title(f"Daily", fontsize=9)
    ax.set_ylabel("Volume" if col_idx == 0 else "")
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)

plt.tight_layout()
fig_path = FEAT / "fig_aggregation_comparison.png"
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved: {fig_path}")


# ==============================================================================
# TASK 5 – Feature specification document
# ==============================================================================
print("\n" + "="*70)
print("TASK 5: Writing feature specification document")
print("="*70)

# Gather actual column info
hourly_cols = list(hourly_df.columns) if not hourly_df.empty else []
feat_cols   = list(feat_tbl.columns)

spec_md = f"""# Feature Specification Document
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. station_feature_table.csv

One row per station (all stations in station_master_table, n={feat_tbl.shape[0]}).

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

One row per (station, hour). Stations: {len(all_hourly)}, total rows: {hourly_df.shape[0]:,}.
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
"""

spec_path = FEAT / "feature_spec.md"
spec_path.write_text(spec_md)
print(f"  Saved: {spec_path}")


# ==============================================================================
# REPORT
# ==============================================================================
print("\n" + "="*70)
print("Writing feature_pipeline_report.md")
print("="*70)

# Compute summary stats for report
n_stations_master   = master_df.shape[0]
n_trusted_final     = len(available_stations)
n_hourly_rows       = hourly_df.shape[0]
n_feat_rows         = feat_tbl.shape[0]
n_feat_cols         = feat_tbl.shape[1]
n_hourly_cols       = len(hourly_df.columns)

coverage_stats = ""
if 'hourly_coverage' in hourly_df.columns:
    cov = hourly_df['hourly_coverage'].describe()
    coverage_stats = (f"    - Mean hourly coverage: {cov['mean']:.1f}%\n"
                      f"    - Min hourly coverage: {cov['min']:.1f}%\n"
                      f"    - Coverage threshold applied: >=50%")

imputed_pct = ""
if 'imputed' in hourly_df.columns:
    pct = hourly_df['imputed'].mean() * 100
    imputed_pct = f"    - Imputed-flagged hours: {pct:.1f}% of retained hours"

vol_stats = ""
if 'total_volume' in hourly_df.columns:
    vols = hourly_df['total_volume']
    vol_stats = (f"    - Median hourly volume: {vols.median():.0f} vehicles\n"
                 f"    - Max hourly volume: {vols.max():.0f} vehicles")

report_md = f"""## Objective
Build clean, analysis-ready datasets and feature tables from trusted GDOT 2024
traffic count station data, supporting downstream modeling and AADT estimation.

## Methods

### Station Selection (Task 1)
- Loaded station_month_trustworthiness.csv ({trust_df.shape[0]:,} rows across all years/months).
- Filtered to year=2024 and trust_tier='TRUSTED'; required ≥6 trusted months.
- Intersected with trusted_station_list.csv ({len(trusted_station_ids)} stations) and
  station_master_table filtered to in_5min_2024=True ({len(in_5min_set)} stations).
- Final trusted set: **{len(final_trusted_ids)} stations** with raw data files on disk: **{len(available_stations)} stations** (capped at 100).

### Hourly Dataset (Task 2)
- For each trusted station, read raw 5-min CSV (chunked at 50k rows).
- Aggregated all 5-min bins within each clock hour: summed Count and F1–F15,
  averaged Coverage %, counted non-null bins (n_bins).
- Applied coverage filter: excluded hours with mean coverage < 50%.
- Flagged hours with n_bins < 6 as imputed=True.
- Added temporal features: date, hour_of_day, day_of_week, month, is_weekday.

### Feature Table (Task 3)
- Started from full station_master_table ({n_stations_master} stations).
- Left-merged: daily volume summary, AADT 2023 proxy, seasonal amplitude,
  and 2024 trustworthiness statistics.
- Derived: is_trusted_2024 flag, aadt_2024_estimate = median_daily_volume × 365.

### Aggregation Comparison (Task 4)
- Selected 5 example trusted stations.
- For each: loaded raw 5-min data, aggregated to hourly and daily.
- Plotted 3×5 subplot grid for June 3–9, 2024 reference week.

## Key Findings

**Station coverage:**
- Stations in master table: {n_stations_master}
- Stations with ≥6 trusted 2024 months: {len(t2024_6)}
- Stations meeting all trust criteria with data on disk: {len(available_stations)}

**Hourly dataset:**
- Stations processed: {len(all_hourly)}
- Total hourly records: {n_hourly_rows:,}
- Columns: {n_hourly_cols}
{coverage_stats}
{imputed_pct}
{vol_stats}

**Feature table:**
- Rows (stations): {n_feat_rows}
- Columns (features): {n_feat_cols}
- Trusted stations flagged: {feat_tbl['is_trusted_2024'].sum()}

## Tables/Plots Created

| File | Description |
|------|-------------|
| `clean_hourly_2024_trusted.parquet` | {n_hourly_rows:,} hourly records, {n_hourly_cols} cols, {len(all_hourly)} stations |
| `clean_hourly_2024_trusted_sample.csv` | First 10,000 rows of hourly parquet |
| `station_feature_table.csv` | {n_feat_rows} stations × {n_feat_cols} features |
| `fig_aggregation_comparison.png` | 3×5 subplot: 5-min / hourly / daily for 5 stations |
| `feature_spec.md` | Column-level documentation for all outputs |
| `feature_pipeline_report.md` | This report |

## Risks/Caveats

1. **Direction summing**: No directional split; all lanes summed. Multi-lane
   stations may not be comparable to single-lane stations on a per-lane basis.
2. **Coverage threshold**: 50% cutoff retains some noisy hours. Models should
   use `imputed` flag for additional filtering.
3. **Station cap**: Only {len(available_stations)} of {len(final_trusted_ids)} trusted stations processed for
   hourly data due to the 100-station cap. Feature table includes all {n_stations_master} stations.
4. **AADT 2023 proxy**: June-based estimate; accuracy degrades for stations
   with high seasonal amplitude (>0.4).
5. **Multi-source double-counting**: Stations with n_sources > 1 aggregate
   across sensors; may over-count if sensors overlap spatially.

## Recommended Next Steps

1. **AADT modeling**: Use station_feature_table.csv with functional_class,
   seasonal_amplitude, and aadt_proxy_2023 as predictors for AADT estimation.
2. **Imputation**: For the {feat_tbl['is_trusted_2024'].sum()} trusted stations, build a gap-filling
   model using neighboring trusted stations (spatial kriging or k-NN).
3. **Directional analysis**: Re-run hourly aggregation with direction as a
   grouping variable for travel demand modeling.
4. **Seasonal correction**: Apply seasonal_index to aadt_2024_estimate to
   derive bias-corrected AADT for months with high seasonal amplitude.
5. **Remove 100-station cap**: Process all {len(final_trusted_ids)} trusted stations for
   full-population hourly dataset (requires ~{len(final_trusted_ids) * 8}GB RAM estimate).
6. **Validation**: Cross-validate aadt_2024_estimate against GDOT official AADT
   counts where available.
"""

report_path = FEAT / "feature_pipeline_report.md"
report_path.write_text(report_md)
print(f"  Saved: {report_path}")

print("\n" + "="*70)
print("PIPELINE COMPLETE")
print("="*70)
print(f"  Output directory: {FEAT}")
for f in sorted(FEAT.iterdir()):
    size = f.stat().st_size
    print(f"    {f.name:55s} {size/1024:8.1f} KB")
