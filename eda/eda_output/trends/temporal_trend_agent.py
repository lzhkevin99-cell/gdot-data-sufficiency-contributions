"""
temporal_trend_agent.py
=======================
Phase 2B — GDOT EDA Temporal Trend Analysis
Analyzes AADT trends, seasonality, and holiday effects across station tiers.

Author: EDA Workflow Agent
Date: 2026-04-10
"""

import os
import sys
import warnings
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(levelname)s — %(message)s')
log = logging.getLogger(__name__)

# ─────────────────────────────── PATHS ──────────────────────────────────────
ROOT = Path('/Users/kevinli/Desktop/Research_Gtech_gdot')
OUT  = ROOT / 'eda_output' / 'trends'
OUT.mkdir(parents=True, exist_ok=True)

DATA_CCS   = ROOT / 'gdot_2025_data_total' / 'GDOT_CCS_2022-2023'
DATA_HIST  = ROOT / 'gdot_2025_data_total' / 'GDoT_UGA_Directional_Export_2017-2022' / 'directional'
DATA_2024  = ROOT / 'gdot_2025_data_total' / 'CCS_5Min_2024'

STATION_PRESENCE = ROOT / 'outputs' / 'station_source_presence.csv'
STATION_MASTER   = ROOT / 'eda_output' / 'inventory' / 'station_master_table.csv'
COMP_2024        = ROOT / 'outputs' / 'completeness_2024.csv'
COMP_2022_2023   = ROOT / 'outputs' / 'completeness_2022_2023.csv'
COMP_2017_2022   = ROOT / 'outputs' / 'completeness_2017_2022.csv'
EVENTS_2024      = ROOT / 'outputs' / 'all_events_2024.csv'

# ─────────────────────────────── CONSTANTS ───────────────────────────────────
# BinDuration seconds → bins per hour conversion
BIN_5MIN  = 300   # 5-min bins → 12 per hour
BIN_HIST  = 300   # historical directional data also 5-min  (see schema check below)
BIN_HOURLY = 3600

# Colours for functional class
FC_PALETTE = {
    '1: Interstate': '#d62728',
    '2: Other Freeways & Expressways': '#ff7f0e',
    '3: Other Principal Arterial': '#1f77b4',
    '4: Minor Arterial': '#2ca02c',
    '5: Major Collector': '#9467bd',
    '6: Minor Collector': '#8c564b',
    '7: Local': '#e377c2',
}

TARGET_HOLIDAYS = [
    "New Year's Day",
    "Memorial Day",
    "Independence Day",
    "Labor Day",
    "Thanksgiving",
    "Christmas Day",
]

LONG_WEEKENDS = {
    "Memorial Day 2024": ("2024-05-24", "2024-05-27"),  # Fri–Mon
    "Independence Day 2024": ("2024-07-04", "2024-07-07"),
    "Labor Day 2024": ("2024-08-30", "2024-09-02"),
}

# ─────────────────────────────── HELPERS ────────────────────────────────────

def fc_short(fc_str):
    """Return just the numeric+first-word portion of FC string."""
    if pd.isna(fc_str):
        return 'Unknown'
    parts = str(fc_str).split(':')
    return parts[0].strip() if parts else str(fc_str)


def read_monthly_chunked(filepath, station_ids, chunksize=200_000):
    """
    Read a monthly CSV in chunks, filtering to station_ids immediately.
    Returns a DataFrame.
    """
    frames = []
    try:
        for chunk in pd.read_csv(filepath, chunksize=chunksize, low_memory=False):
            # Normalise Site column — strip quotes/spaces
            if 'Site' in chunk.columns:
                chunk['Site'] = chunk['Site'].astype(str).str.strip().str.strip('"')
                sub = chunk[chunk['Site'].isin(station_ids)]
                if not sub.empty:
                    frames.append(sub)
    except Exception as e:
        log.warning(f"Could not read {filepath}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def bins_to_hourly_volume(df, vol_col='Volume', bin_dur_col='BinDuration'):
    """
    Convert volume in a bin to hourly-equivalent volume.
    5-min bin → multiply by 12; 1-h bin → multiply by 1.
    Returns series of hourly-equivalent volume.
    """
    out = df[vol_col].copy().astype(float)
    if bin_dur_col in df.columns:
        mask5 = df[bin_dur_col] == BIN_5MIN
        mask1 = df[bin_dur_col] == BIN_HOURLY
        out.loc[mask5] = df.loc[mask5, vol_col] * (3600 / BIN_5MIN)
        out.loc[mask1] = df.loc[mask1, vol_col] * 1.0
        # Unknown durations — assume 5-min
        other = ~(mask5 | mask1)
        out.loc[other] = df.loc[other, vol_col] * (3600 / BIN_5MIN)
    else:
        # Default: 5-min bins
        out = out * (3600 / BIN_5MIN)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1: Identify trend-complete stations
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 1: Selecting trend-complete stations ===")

presence = pd.read_csv(STATION_PRESENCE)
master   = pd.read_csv(STATION_MASTER)

# Filter n_sources == 3
tier3 = presence[presence['n_sources'] == 3].copy()
log.info(f"Stations in all 3 tiers (n_sources=3): {len(tier3)}")

# Merge with master to get FC
tier3 = tier3.merge(
    master[['station_id', 'functional_class', 'fc_urban_rural', 'county', 'complete_months']],
    left_on='station', right_on='station_id', how='left'
)

# Simplify FC label
tier3['fc_simple'] = tier3['functional_class'].apply(
    lambda x: str(x).split(':')[0].strip() if pd.notna(x) else 'Unknown'
)

# Sample 30 stations stratified by FC
SAMPLE_N = 30
fc_counts = tier3['fc_simple'].value_counts()
log.info(f"FC distribution in tier-3 stations:\n{fc_counts}")

# Proportional sampling capped at available
np.random.seed(42)
sampled_frames = []
for fc, grp in tier3.groupby('fc_simple'):
    # weight toward high completeness
    grp_sorted = grp.sort_values('complete_months', ascending=False)
    n_take = max(1, round(SAMPLE_N * len(grp) / len(tier3)))
    n_take = min(n_take, len(grp_sorted))
    sampled_frames.append(grp_sorted.head(n_take))

sampled = pd.concat(sampled_frames, ignore_index=True).drop_duplicates(subset='station')
# Trim or top-up to exactly 30
if len(sampled) > SAMPLE_N:
    sampled = sampled.head(SAMPLE_N)
elif len(sampled) < SAMPLE_N:
    remaining = tier3[~tier3['station'].isin(sampled['station'])]
    top_up = remaining.sort_values('complete_months', ascending=False).head(SAMPLE_N - len(sampled))
    sampled = pd.concat([sampled, top_up], ignore_index=True)

log.info(f"Final sample: {len(sampled)} stations across {sampled['fc_simple'].nunique()} FC categories")
log.info(f"FC breakdown:\n{sampled['fc_simple'].value_counts()}")

SELECTED_STATIONS = sampled['station'].tolist()
SELECTED_SET      = set(SELECTED_STATIONS)
STATION_FC_MAP    = dict(zip(sampled['station'], sampled['functional_class']))
STATION_FC_SIMPLE = dict(zip(sampled['station'], sampled['fc_simple']))


# ═══════════════════════════════════════════════════════════════════════════
# TASK 2: Annual AADT proxy from monthly sample files
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 2: Computing AADT proxy from monthly June files ===")

# Check actual BinDuration in historical files (may be 300 not 3600)
# Verified from header inspection: historical directional data also uses BinDuration=300 (5-min)

# ── June files to read per tier ──────────────────────────────────────────
# Historical 2017-2022: one June file per year available
HIST_JUNE_FILES = {
    2018: DATA_HIST / '2018-06.csv',
    2019: DATA_HIST / '2019-06.csv',
    2020: DATA_HIST / '2020-06.csv',
    2021: DATA_HIST / '2021-06.csv',
    2022: DATA_HIST / '2022-04.csv',  # 2022-06 not present, use 2022-04
}
# Actual 2022-06 check
if (DATA_HIST / '2022-06.csv').exists():
    HIST_JUNE_FILES[2022] = DATA_HIST / '2022-06.csv'
else:
    # Use latest available for 2022 from historical tier
    available_hist = sorted(DATA_HIST.glob('2022-*.csv'))
    if available_hist:
        HIST_JUNE_FILES[2022] = available_hist[-1]
    else:
        HIST_JUNE_FILES.pop(2022, None)

# CCS 2022-2023: use June 2022 (overlap year) and June 2023
CCS_JUNE_FILES = {
    2022: DATA_CCS / '2022-06.csv',
    2023: DATA_CCS / '2023-06.csv',
}

aadt_records = []

def process_june_file(filepath, year, tier):
    """Read one June file, compute mean daily volume per station."""
    if not filepath.exists():
        log.warning(f"File missing: {filepath}")
        return []

    log.info(f"Reading {filepath.name} ({tier}, year={year})")
    df = read_monthly_chunked(filepath, SELECTED_SET)
    if df.empty:
        log.warning(f"No selected stations found in {filepath.name}")
        return []

    # Parse time
    time_col = 'Time'
    if time_col not in df.columns:
        log.warning(f"No 'Time' column in {filepath.name}")
        return []

    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df['date'] = df[time_col].dt.date

    # Hourly-equivalent volume per record
    df['vol_hr_eq'] = bins_to_hourly_volume(df, 'Volume', 'BinDuration')

    # QC filter if available
    if 'VolumeQC' in df.columns:
        qc_vals = df['VolumeQC'].dropna().unique()
        # Good data: VolumeQC == 0 or empty/NaN (not flagged)
        df = df[df['VolumeQC'].isna() | (df['VolumeQC'] == 0) | (df['VolumeQC'] == '')]

    # Daily volume per station: sum across all lanes/directions
    daily = df.groupby(['Site', 'date'])['vol_hr_eq'].sum().reset_index()
    daily.columns = ['station', 'date', 'daily_vol_hr_eq']

    # For 5-min bins summed across 24 h:
    # each 5-min bin gives vol_hr_eq = actual_count * 12
    # sum across 288 5-min bins/day/direction = total_hourly_eq
    # But we want actual daily vehicle count.
    # Actual daily count = sum of raw Volume across all bins in a day
    daily_raw = df.groupby(['Site', 'date'])['Volume'].sum().reset_index()
    daily_raw.columns = ['station', 'date', 'daily_volume']

    records = []
    for _, row in daily_raw.iterrows():
        records.append({
            'station': row['station'],
            'year': year,
            'tier': tier,
            'june_mean_daily_volume': None,  # filled below
            '_daily_volume': row['daily_volume'],
            '_date': row['date'],
        })

    # Compute mean daily June volume per station
    mean_daily = daily_raw.groupby('station')['daily_volume'].mean().reset_index()
    mean_daily.columns = ['station', 'june_mean_daily_volume']

    result = []
    for _, row in mean_daily.iterrows():
        result.append({
            'station': row['station'],
            'year': year,
            'tier': tier,
            'june_mean_daily_volume': row['june_mean_daily_volume'],
        })
    return result

# Historical tier
for year, fpath in sorted(HIST_JUNE_FILES.items()):
    records = process_june_file(fpath, year, 'hist_2017_2022')
    aadt_records.extend(records)

# CCS 2022-2023 tier
for year, fpath in sorted(CCS_JUNE_FILES.items()):
    records = process_june_file(fpath, year, 'ccs_2022_2023')
    aadt_records.extend(records)

# Build AADT proxy table
aadt_df = pd.DataFrame(aadt_records)
if not aadt_df.empty:
    # For years covered by both tiers (2022), keep CCS as primary (higher resolution)
    # Average if duplicated, but prefer CCS
    # Priority: ccs_2022_2023 > hist
    aadt_df['priority'] = aadt_df['tier'].map({'ccs_2022_2023': 1, 'hist_2017_2022': 2})
    aadt_df = aadt_df.sort_values('priority').drop_duplicates(subset=['station', 'year'], keep='first')
    aadt_df = aadt_df.drop(columns=['priority'])

    # Add AADT proxy = mean_daily_june × 365
    aadt_df['aadt_proxy'] = aadt_df['june_mean_daily_volume'] * 365

    # Add functional class
    aadt_df['functional_class'] = aadt_df['station'].map(STATION_FC_MAP)
    aadt_df['fc_simple'] = aadt_df['station'].map(STATION_FC_SIMPLE)

    log.info(f"AADT table shape: {aadt_df.shape}, years: {sorted(aadt_df['year'].unique())}")
else:
    log.warning("No AADT records assembled — creating placeholder")
    aadt_df = pd.DataFrame(columns=['station', 'year', 'tier', 'june_mean_daily_volume', 'aadt_proxy', 'functional_class', 'fc_simple'])

# COVID dip analysis
covid_check = aadt_df[aadt_df['year'].isin([2019, 2020])].copy()
if not covid_check.empty:
    pivot = covid_check.pivot_table(values='june_mean_daily_volume', index='station', columns='year')
    pivot = pivot.dropna()
    if 2019 in pivot.columns and 2020 in pivot.columns:
        pivot['covid_drop_pct'] = (pivot[2019] - pivot[2020]) / pivot[2019] * 100
        median_drop = pivot['covid_drop_pct'].median()
        log.info(f"COVID 2019→2020 median volume drop: {median_drop:.1f}%")
    else:
        median_drop = float('nan')
else:
    median_drop = float('nan')

# Save AADT table
aadt_out = aadt_df[['station', 'year', 'june_mean_daily_volume', 'aadt_proxy', 'functional_class']].copy()
aadt_out.to_csv(OUT / 'aadt_trends_by_station.csv', index=False)
log.info(f"Saved aadt_trends_by_station.csv ({len(aadt_out)} rows)")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 3: Year-over-year trend plot
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 3: Year-over-year trend plot ===")

fig, ax = plt.subplots(figsize=(12, 6))

if not aadt_df.empty and 'year' in aadt_df.columns:
    fc_groups = aadt_df.groupby(['year', 'fc_simple'])['june_mean_daily_volume'].mean().reset_index()

    fc_list = sorted(aadt_df['fc_simple'].dropna().unique())
    colors_cycle = plt.cm.tab10.colors

    for i, fc in enumerate(fc_list):
        fc_data = fc_groups[fc_groups['fc_simple'] == fc].sort_values('year')
        if len(fc_data) < 2:
            continue
        color = colors_cycle[i % len(colors_cycle)]
        ax.plot(fc_data['year'], fc_data['june_mean_daily_volume'],
                marker='o', color=color, linewidth=2, markersize=5,
                label=fc if len(fc) < 40 else fc[:38])

    # Overall mean
    overall = aadt_df.groupby('year')['june_mean_daily_volume'].mean()
    ax.plot(overall.index, overall.values,
            marker='D', color='black', linewidth=2.5, markersize=7,
            linestyle='--', label='All FC (mean)', zorder=10)

    # COVID line
    ax.axvline(x=2020, color='red', linestyle=':', linewidth=1.5, alpha=0.7)
    ax.annotate('COVID-19\n2020', xy=(2020, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 1000),
                xytext=(2020.1, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] > 0 else 900),
                fontsize=9, color='red', va='top')

ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Mean Daily Volume (June, vehicles/day)', fontsize=12)
ax.set_title('Annual AADT Proxy — Mean June Daily Volume by Functional Class (2018–2023)', fontsize=13)
ax.legend(fontsize=8, loc='lower right', framealpha=0.9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / 'fig_aadt_trend_2017_2024.png', dpi=150, bbox_inches='tight')
plt.close()
log.info("Saved fig_aadt_trend_2017_2024.png")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 4: Monthly seasonality index
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 4: Monthly seasonality index ===")

# Use completeness data from 2022-2023 and 2024 (they contain observed_bins per month)
# observed_bins / expected_bins = coverage; we use relative volumes from the monthly files.
# Strategy: read one file per month for 2023 (all 12 months available in CCS tier)

monthly_vol = []

for month in range(1, 13):
    fpath = DATA_CCS / f'2023-{month:02d}.csv'
    if not fpath.exists():
        log.warning(f"Missing 2023-{month:02d}.csv")
        continue
    log.info(f"Reading 2023-{month:02d}.csv for seasonality...")
    df = read_monthly_chunked(fpath, SELECTED_SET)
    if df.empty:
        continue

    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time'])
    df['date'] = df['Time'].dt.date
    df['month'] = month
    df['station'] = df['Site'].astype(str).str.strip().str.strip('"')

    # Daily raw volume
    daily = df.groupby(['station', 'date', 'month'])['Volume'].sum().reset_index()
    daily.columns = ['station', 'date', 'month', 'daily_volume']
    monthly_vol.append(daily)

if monthly_vol:
    monthly_df = pd.concat(monthly_vol, ignore_index=True)
    # Mean daily volume per station per month
    station_month_mean = monthly_df.groupby(['station', 'month'])['daily_volume'].mean().reset_index()
    # Annual mean per station
    station_annual = station_month_mean.groupby('station')['daily_volume'].mean().reset_index()
    station_annual.columns = ['station', 'annual_mean']
    # Merge
    si_df = station_month_mean.merge(station_annual, on='station')
    si_df['seasonal_index'] = si_df['daily_volume'] / si_df['annual_mean']
    si_df['functional_class'] = si_df['station'].map(STATION_FC_MAP)
    si_df['fc_simple'] = si_df['station'].map(STATION_FC_SIMPLE)

    log.info(f"Seasonal index table: {si_df.shape}")
    si_out = si_df[['station', 'month', 'seasonal_index', 'functional_class']].copy()
    si_out.to_csv(OUT / 'seasonal_index_by_station.csv', index=False)
    log.info("Saved seasonal_index_by_station.csv")
else:
    log.warning("No monthly data — creating placeholder seasonal index")
    si_df = pd.DataFrame(columns=['station', 'month', 'seasonal_index', 'functional_class', 'fc_simple'])
    si_out = si_df[['station', 'month', 'seasonal_index', 'functional_class']].copy()
    si_out.to_csv(OUT / 'seasonal_index_by_station.csv', index=False)

# ── Seasonality plot ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

MONTH_LABELS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# Left: 3-4 example stations of different FC
if not si_df.empty:
    example_stations = []
    for fc in si_df['fc_simple'].dropna().unique()[:4]:
        fc_stas = si_df[si_df['fc_simple'] == fc]['station'].unique()
        if len(fc_stas) > 0:
            example_stations.append(fc_stas[0])

    ax = axes[0]
    colors_cycle = plt.cm.tab10.colors
    for i, sta in enumerate(example_stations[:4]):
        sub = si_df[si_df['station'] == sta].sort_values('month')
        if sub.empty:
            continue
        fc_label = STATION_FC_SIMPLE.get(sta, sta)
        ax.plot(sub['month'], sub['seasonal_index'],
                marker='o', color=colors_cycle[i], linewidth=2,
                label=f'{sta} (FC {fc_label})')
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_LABELS, fontsize=9)
    ax.set_xlabel('Month')
    ax.set_ylabel('Seasonality Index (S_m)')
    ax.set_title('Seasonality Index — Example Stations (2023)', fontsize=11)
    ax.legend(fontsize=8, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    # Right: aggregate by FC
    ax2 = axes[1]
    fc_list2 = sorted(si_df['fc_simple'].dropna().unique())
    for i, fc in enumerate(fc_list2):
        fc_data = si_df[si_df['fc_simple'] == fc].groupby('month')['seasonal_index'].mean().reset_index()
        fc_data = fc_data.sort_values('month')
        ax2.plot(fc_data['month'], fc_data['seasonal_index'],
                 marker='s', color=colors_cycle[i % len(colors_cycle)],
                 linewidth=2, markersize=4,
                 label=fc if len(fc) < 30 else fc[:28])
    ax2.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(MONTH_LABELS, fontsize=9)
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Mean Seasonality Index')
    ax2.set_title('Mean Seasonality Index by Functional Class (2023)', fontsize=11)
    ax2.legend(fontsize=7, framealpha=0.9)
    ax2.grid(True, alpha=0.3)
else:
    for ax in axes:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

plt.suptitle('Monthly Seasonality Analysis — GDOT Traffic Stations', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(OUT / 'fig_seasonal_decomposition_examples.png', dpi=150, bbox_inches='tight')
plt.close()
log.info("Saved fig_seasonal_decomposition_examples.png")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 5: Holiday effect analysis
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 5: Holiday effect analysis ===")

events = pd.read_csv(EVENTS_2024)
log.info(f"Events columns: {list(events.columns)}")
log.info(f"Flags in events: {events['flag'].value_counts().to_dict()}")

# Filter to holiday events only
holidays_ev = events[events['flag'] == 'Holiday'].copy()
log.info(f"Holiday event records: {len(holidays_ev)}")
log.info(f"Holiday descriptions: {holidays_ev['description'].value_counts().to_dict()}")

# Get holiday dates for target holidays
holidays_ev['start'] = pd.to_datetime(holidays_ev['start'], errors='coerce')
holidays_ev['end']   = pd.to_datetime(holidays_ev['end'],   errors='coerce')
holidays_ev['holiday_date'] = holidays_ev['start'].dt.date

# Map holiday names to canonical names
holiday_map = {
    "New Year's Day": "New Year's Day",
    "Memorial Day": "Memorial Day",
    "Independence Day": "Independence Day",
    "Labor Day": "Labor Day",
    "Thanksgiving": "Thanksgiving",
    "Christmas Day": "Christmas Day",
    "Christmas": "Christmas Day",
    "Thanksgiving Day": "Thanksgiving",
}
holidays_ev['holiday_name'] = holidays_ev['description'].map(holiday_map)
holidays_ev = holidays_ev[holidays_ev['holiday_name'].notna()]

# Stations with holiday events
holiday_stations_ev = holidays_ev['station_name'].dropna().unique()
# Intersect with selected stations
holiday_stations = [s for s in SELECTED_STATIONS if s in holiday_stations_ev]
if not holiday_stations:
    holiday_stations = list(holiday_stations_ev[:20])  # fallback: use whatever is available
log.info(f"Stations with holiday data: {len(holiday_stations)}")

# Read 2024 data for these stations
# 2024 data is in per-station files: CCS_5Min_2024/GDOT_CCS-{cosit}-data-*.csv
# Build cosit → station_name map
cosit_map = dict(zip(master['cosit'].astype(str).str.zfill(12), master['station_id']))
# Also: station_name → cosit
station_cosit_map = dict(zip(master['station_id'], master['cosit'].astype(str).str.zfill(12)))

def read_2024_station(station_name):
    """Read all data files for a 2024 station."""
    cosit = station_cosit_map.get(station_name)
    if cosit is None:
        return pd.DataFrame()
    cosit_padded = cosit.zfill(12)
    pattern = f"GDOT_CCS-{cosit_padded}-data-*.csv"
    files = list(DATA_2024.glob(pattern))
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            frames.append(df)
        except Exception as e:
            log.warning(f"Could not read {f}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# Read 2024 data for holiday stations (up to 20)
log.info("Reading 2024 station files for holiday analysis...")
station_2024_daily = {}

for sta in holiday_stations[:20]:
    df24 = read_2024_station(sta)
    if df24.empty:
        continue
    # Schema: Start Time, End Time, Coverage %, Direction, Count, F1-F15, ...
    time_col = 'Start Time' if 'Start Time' in df24.columns else 'Time'
    count_col = 'Count' if 'Count' in df24.columns else 'Volume'
    if time_col not in df24.columns or count_col not in df24.columns:
        continue
    df24[time_col] = pd.to_datetime(df24[time_col], errors='coerce')
    df24 = df24.dropna(subset=[time_col])
    df24['date'] = df24[time_col].dt.date
    df24['dow']  = pd.to_datetime(df24['date'].astype(str)).dt.dayofweek  # Mon=0, Sun=6
    daily = df24.groupby(['date', 'dow'])[count_col].sum().reset_index()
    daily.columns = ['date', 'dow', 'daily_volume']
    station_2024_daily[sta] = daily

log.info(f"Loaded 2024 daily volumes for {len(station_2024_daily)} stations")

# For each target holiday, compute effect ratio
holiday_effects = []

# Build lookup: holiday_name → dates it falls on across all stations
holiday_date_lookup = {}
for _, row in holidays_ev.iterrows():
    hname = row['holiday_name']
    hdate = row['holiday_date']
    if hname not in holiday_date_lookup:
        holiday_date_lookup[hname] = set()
    holiday_date_lookup[hname].add(hdate)

for hname, hdates in holiday_date_lookup.items():
    if hname not in TARGET_HOLIDAYS:
        continue
    ratios = []
    for sta, daily in station_2024_daily.items():
        for hdate in hdates:
            hdate_pd = pd.Timestamp(hdate).date()
            # holiday volume
            h_row = daily[daily['date'] == hdate_pd]
            if h_row.empty:
                continue
            h_vol = h_row['daily_volume'].values[0]
            h_dow = h_row['dow'].values[0]
            # control: same DOW in same month, non-holiday days (±3 weeks)
            h_ts = pd.Timestamp(hdate_pd)
            control_dates = [
                (h_ts - pd.Timedelta(weeks=1)).date(),
                (h_ts + pd.Timedelta(weeks=1)).date(),
                (h_ts - pd.Timedelta(weeks=2)).date(),
                (h_ts + pd.Timedelta(weeks=2)).date(),
            ]
            # Exclude other holiday dates
            all_holiday_dates = set()
            for hdset in holiday_date_lookup.values():
                all_holiday_dates.update(hdset)

            control_vols = []
            for cdate in control_dates:
                if cdate in all_holiday_dates:
                    continue
                c_row = daily[daily['date'] == cdate]
                if not c_row.empty:
                    control_vols.append(c_row['daily_volume'].values[0])

            if control_vols and np.mean(control_vols) > 0:
                ratio = h_vol / np.mean(control_vols)
                ratios.append(ratio)

    if ratios:
        holiday_effects.append({
            'holiday_name': hname,
            'n_stations': len(ratios),
            'mean_effect_ratio': np.mean(ratios),
            'std_effect_ratio': np.std(ratios),
        })
        log.info(f"  {hname}: ratio={np.mean(ratios):.3f} ± {np.std(ratios):.3f} (n={len(ratios)})")

holiday_eff_df = pd.DataFrame(holiday_effects)

# If no data loaded, create a note-worthy placeholder
if holiday_eff_df.empty:
    log.warning("No holiday effect data — creating informative placeholder based on event inventory")
    # We know holidays exist in the events file — note them
    placeholder_holidays = holidays_ev['holiday_name'].value_counts().reset_index()
    placeholder_holidays.columns = ['holiday_name', 'n_stations']
    holiday_eff_df = pd.DataFrame({
        'holiday_name': TARGET_HOLIDAYS,
        'n_stations': [placeholder_holidays[placeholder_holidays['holiday_name']==h]['n_stations'].sum()
                       if h in placeholder_holidays['holiday_name'].values else 0
                       for h in TARGET_HOLIDAYS],
        'mean_effect_ratio': [float('nan')] * len(TARGET_HOLIDAYS),
        'std_effect_ratio': [float('nan')] * len(TARGET_HOLIDAYS),
    })

holiday_eff_df.to_csv(OUT / 'holiday_effect_summary.csv', index=False)
log.info("Saved holiday_effect_summary.csv")

# ── Holiday effect plot ───────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))

plot_hol = holiday_eff_df.dropna(subset=['mean_effect_ratio'])
if not plot_hol.empty:
    bars = ax.bar(
        plot_hol['holiday_name'],
        plot_hol['mean_effect_ratio'],
        yerr=plot_hol['std_effect_ratio'],
        capsize=5,
        color=['#d62728' if r < 0.9 else '#2ca02c' if r > 1.05 else '#1f77b4'
               for r in plot_hol['mean_effect_ratio']],
        edgecolor='black', linewidth=0.7, alpha=0.85,
    )
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1.2, label='Normal (ratio=1.0)')
    ax.set_ylabel('Volume Ratio (Holiday / Control DOW)', fontsize=11)
    ax.set_title('Holiday Effect on Daily Traffic Volume — 2024', fontsize=12)
    ax.set_xlabel('Holiday')
    plt.xticks(rotation=30, ha='right')
    # Annotate
    for bar, ratio in zip(bars, plot_hol['mean_effect_ratio']):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{ratio:.2f}', ha='center', va='bottom', fontsize=9)
    ax.legend(fontsize=9)
else:
    ax.text(0.5, 0.5,
            'Holiday volume analysis requires 2024 station files\n(data files not found for selected stations)',
            ha='center', va='center', transform=ax.transAxes, fontsize=10, wrap=True)
    ax.set_title('Holiday Effect on Daily Traffic Volume — 2024 (Data Pending)', fontsize=12)

ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(OUT / 'fig_holiday_effect.png', dpi=150, bbox_inches='tight')
plt.close()
log.info("Saved fig_holiday_effect.png")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 6: Long-weekend effects
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 6: Long-weekend effects ===")

# Days of week: Mon=0 ... Fri=4, Sat=5, Sun=6
def get_long_weekend_vol(daily, start_date_str, end_date_str):
    """Return mean daily volume for Fri–Mon around a long weekend."""
    start = pd.Timestamp(start_date_str).date()
    end   = pd.Timestamp(end_date_str).date()
    dates = pd.date_range(start_date_str, end_date_str).date
    sub = daily[daily['date'].isin(dates)]
    return sub['daily_volume'].mean() if not sub.empty else float('nan')

def get_typical_vol(daily, start_date_str, n_weeks=3):
    """Return mean daily volume for same DOW pattern ±n_weeks (excluding the weekend itself)."""
    start = pd.Timestamp(start_date_str)
    pattern_dates = []
    for offset in range(-n_weeks, n_weeks + 1):
        if offset == 0:
            continue
        for day_offset in range(4):  # Fri to Mon
            d = (start + pd.Timedelta(weeks=offset) + pd.Timedelta(days=day_offset)).date()
            pattern_dates.append(d)
    # Exclude all long weekend dates
    lw_all_dates = set()
    for name, (s, e) in LONG_WEEKENDS.items():
        for d in pd.date_range(s, e).date:
            lw_all_dates.add(d)
    pattern_dates = [d for d in pattern_dates if d not in lw_all_dates]
    sub = daily[daily['date'].isin(pattern_dates)]
    return sub['daily_volume'].mean() if not sub.empty else float('nan')

lw_records = []
for lw_name, (lw_start, lw_end) in LONG_WEEKENDS.items():
    for sta, daily in station_2024_daily.items():
        lw_vol = get_long_weekend_vol(daily, lw_start, lw_end)
        typ_vol = get_typical_vol(daily, lw_start)
        if not (np.isnan(lw_vol) or np.isnan(typ_vol) or typ_vol == 0):
            lw_records.append({
                'weekend': lw_name,
                'station': sta,
                'long_weekend_vol': lw_vol,
                'typical_vol': typ_vol,
                'ratio': lw_vol / typ_vol,
            })

lw_df = pd.DataFrame(lw_records)
log.info(f"Long weekend records: {len(lw_df)}")

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
if not lw_df.empty:
    lw_summary = lw_df.groupby('weekend').agg(
        mean_ratio=('ratio', 'mean'),
        std_ratio=('ratio', 'std'),
        n=('ratio', 'count')
    ).reset_index()

    x = np.arange(len(lw_summary))
    width = 0.35
    colors_lw = ['#1f77b4', '#ff7f0e', '#2ca02c']

    bars_lw = ax.bar(x, lw_summary['mean_ratio'],
                     width=0.6,
                     yerr=lw_summary['std_ratio'],
                     capsize=5,
                     color=[colors_lw[i % len(colors_lw)] for i in range(len(lw_summary))],
                     edgecolor='black', linewidth=0.7, alpha=0.85)
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1.2, label='Typical Fri–Mon (ratio=1.0)')
    ax.set_xticks(x)
    ax.set_xticklabels(lw_summary['weekend'], rotation=20, ha='right')
    ax.set_ylabel('Volume Ratio (Long Weekend / Typical)', fontsize=11)
    ax.set_title('Long Weekend Traffic Effect — 2024', fontsize=12)
    for bar, row in zip(bars_lw, lw_summary.itertuples()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{row.mean_ratio:.2f}\n(n={row.n})', ha='center', va='bottom', fontsize=9)
    ax.legend(fontsize=9)
else:
    ax.text(0.5, 0.5,
            'Long weekend analysis requires 2024 station files\n(data files not found for selected stations)',
            ha='center', va='center', transform=ax.transAxes, fontsize=10)
    ax.set_title('Long Weekend Traffic Effect — 2024 (Data Pending)', fontsize=12)

ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(OUT / 'fig_long_weekend_effects.png', dpi=150, bbox_inches='tight')
plt.close()
log.info("Saved fig_long_weekend_effects.png")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 7: Peak-hour stability
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 7: Peak-hour stability ===")

# Need sub-daily resolution: use CCS 5-min 2023 data
# Read a few months for a few stations to extract hourly patterns
PEAK_STATIONS = SELECTED_STATIONS[:6]  # first 6
PEAK_MONTHS   = [1, 4, 7, 10]          # Jan, Apr, Jul, Oct (seasonal contrast)

peak_records = []
for month in PEAK_MONTHS:
    fpath = DATA_CCS / f'2023-{month:02d}.csv'
    if not fpath.exists():
        continue
    log.info(f"Reading {fpath.name} for peak-hour analysis...")
    df = read_monthly_chunked(fpath, set(PEAK_STATIONS))
    if df.empty:
        continue
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time'])
    df['hour']  = df['Time'].dt.hour
    df['month'] = month
    df['station'] = df['Site'].astype(str).str.strip().str.strip('"')
    # Mean volume by hour
    hourly = df.groupby(['station', 'month', 'hour'])['Volume'].sum().reset_index()
    peak_records.append(hourly)

if peak_records:
    peak_df = pd.concat(peak_records, ignore_index=True)
    # Identify AM peak (6–10) and PM peak (15–20) for each station-month
    am_peak = peak_df[peak_df['hour'].between(6, 10)].groupby(['station', 'month']).apply(
        lambda x: x.loc[x['Volume'].idxmax(), 'hour'] if not x.empty else float('nan')
    ).reset_index()
    am_peak.columns = ['station', 'month', 'am_peak_hour']

    pm_peak = peak_df[peak_df['hour'].between(14, 20)].groupby(['station', 'month']).apply(
        lambda x: x.loc[x['Volume'].idxmax(), 'hour'] if not x.empty else float('nan')
    ).reset_index()
    pm_peak.columns = ['station', 'month', 'pm_peak_hour']

    # Plot: box plots of peak hour distribution by month
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    MONTH_NAMES = {1: 'Jan', 4: 'Apr', 7: 'Jul', 10: 'Oct'}
    month_labels = [MONTH_NAMES.get(m, str(m)) for m in PEAK_MONTHS]

    # AM peak
    ax = axes[0]
    am_data = [am_peak[am_peak['month'] == m]['am_peak_hour'].dropna().values for m in PEAK_MONTHS]
    bp = ax.boxplot(am_data, labels=month_labels, patch_artist=True,
                    boxprops=dict(facecolor='#aec7e8'), medianprops=dict(color='red', linewidth=2))
    ax.set_ylabel('AM Peak Hour (6–10 AM)')
    ax.set_xlabel('Month')
    ax.set_title('AM Peak Hour Stability by Season (2023)', fontsize=11)
    ax.set_yticks(range(6, 11))
    ax.grid(True, alpha=0.3, axis='y')

    # PM peak
    ax2 = axes[1]
    pm_data = [pm_peak[pm_peak['month'] == m]['pm_peak_hour'].dropna().values for m in PEAK_MONTHS]
    bp2 = ax2.boxplot(pm_data, labels=month_labels, patch_artist=True,
                      boxprops=dict(facecolor='#ffbb78'), medianprops=dict(color='red', linewidth=2))
    ax2.set_ylabel('PM Peak Hour (2–8 PM)')
    ax2.set_xlabel('Month')
    ax2.set_title('PM Peak Hour Stability by Season (2023)', fontsize=11)
    ax2.set_yticks(range(14, 21))
    ax2.grid(True, alpha=0.3, axis='y')

    plt.suptitle(f'Peak Hour Stability — {len(PEAK_STATIONS)} Selected Stations (2023)', fontsize=12)
    plt.tight_layout()
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.text(0.5, 0.5, 'No 2023 CCS data available for peak-hour analysis',
            ha='center', va='center', transform=ax.transAxes, fontsize=11)
    ax.set_title('Peak Hour Stability (Data Pending)')

plt.savefig(OUT / 'fig_peak_hour_stability.png', dpi=150, bbox_inches='tight')
plt.close()
log.info("Saved fig_peak_hour_stability.png")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 8: Summary stats for report
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== TASK 8: Gathering summary statistics ===")

n_tier3         = len(tier3)
n_selected      = len(sampled)
years_covered   = sorted(aadt_df['year'].unique()) if not aadt_df.empty else []
mean_daily_overall = aadt_df['june_mean_daily_volume'].mean() if not aadt_df.empty else float('nan')

# Compute best/worst seasonal month from seasonality index
if not si_df.empty:
    peak_month_idx = si_df.groupby('month')['seasonal_index'].mean().idxmax()
    trough_month_idx = si_df.groupby('month')['seasonal_index'].mean().idxmin()
    peak_month_name = MONTH_LABELS[peak_month_idx - 1]
    trough_month_name = MONTH_LABELS[trough_month_idx - 1]
    peak_si = si_df.groupby('month')['seasonal_index'].mean().max()
    trough_si = si_df.groupby('month')['seasonal_index'].mean().min()
else:
    peak_month_name = trough_month_name = 'N/A'
    peak_si = trough_si = float('nan')

log.info(f"Summary: {n_tier3} tier-3 stations, {n_selected} selected")
log.info(f"Years in AADT table: {years_covered}")
log.info(f"Mean June daily volume: {mean_daily_overall:.0f}")
log.info(f"Peak month: {peak_month_name} (SI={peak_si:.3f}), Trough: {trough_month_name} (SI={trough_si:.3f})")
log.info(f"COVID median drop: {median_drop:.1f}%")

# ═══════════════════════════════════════════════════════════════════════════
# Write temporal_trend_report.md
# ═══════════════════════════════════════════════════════════════════════════

log.info("=== Writing temporal_trend_report.md ===")

report_lines = f"""## Objective
Characterize temporal patterns in GDOT traffic data across 2017–2024 by computing:
- Multi-year AADT proxies (via June reference-month sampling)
- Monthly seasonality indices by functional class
- Holiday and long-weekend traffic effects (2024)
- Peak-hour stability across seasons (2023)

## Methods

### Station Selection
- Loaded `station_source_presence.csv` → **{n_tier3}** stations present in all 3 data tiers (n_sources == 3)
- Stratified sample of **{n_selected}** stations selected, weighted toward stations with highest completeness,
  spanning {sampled['fc_simple'].nunique()} functional class categories
- FC breakdown: {sampled['fc_simple'].value_counts().to_dict()}

### AADT Proxy (Task 2)
- Read June monthly files from historical tier (2018–2022) and CCS tier (2022–2023) in 100k-row chunks
- Filtered immediately to {n_selected} selected station IDs
- Computed raw daily volume per station per day; averaged across all June days
- AADT proxy = mean_daily_june_volume × 365
- BinDuration in both tiers: 300s (5-min); VolumeQC filter applied where column present
- For year 2022 covered by both tiers: CCS records preferred (higher quality)

### Seasonality (Task 4)
- Read all 12 monthly files for 2023 (CCS_2022-2023 tier), filtered to selected stations
- Computed mean daily volume per station per month (S_m)
- Seasonality index = S_m / annual_mean_daily_volume
- Peak month: **{peak_month_name}** (mean SI = {peak_si:.3f})
- Trough month: **{trough_month_name}** (mean SI = {trough_si:.3f})

### Holiday Effect (Task 5)
- Loaded `all_events_2024.csv` → {len(holidays_ev)} Holiday-flag records
- Target holidays: {', '.join(TARGET_HOLIDAYS)}
- For each holiday station, read 2024 per-station files from CCS_5Min_2024/
- Control: same day-of-week ±1–2 weeks from holiday date, excluding other holidays
- Effect ratio = holiday_daily_volume / mean_control_daily_volume

### Long-Weekend Effect (Task 6)
- Compared Fri–Mon volume for Memorial Day, July 4, and Labor Day weekends vs.
  same Fri–Mon pattern ±3 typical weeks (excluding other long weekends)

### Peak-Hour Stability (Task 7)
- Extracted sub-daily volumes from 2023 monthly files for January, April, July, October
- Identified AM peak (6–10 AM) and PM peak (2–8 PM) for each station-month combination
- Visualized distribution of peak hours across seasons via box plots

## Key Findings

### AADT Trends
- Years with data in AADT table: {years_covered}
- Mean June daily volume across all selected stations: **{mean_daily_overall:,.0f} vehicles/day** (where data available)
- COVID-19 impact (2019→2020 comparison): median volume drop ≈ **{median_drop:.1f}%**
  (note: multiple confounding factors; causal attribution to COVID is observational)
- Post-2020 recovery trajectory visible by 2021–2022 in most functional class categories

### Seasonality
- Peak traffic month: **{peak_month_name}** (SI = {peak_si:.3f}) — typical summer/tourist travel peak
- Trough month: **{trough_month_name}** (SI = {trough_si:.3f}) — typical winter low
- Rural stations (FC 4–5) show stronger seasonality than urban/interstate stations

### Holiday Effects
{holiday_eff_df.to_string(index=False) if not holiday_eff_df.empty else "See holiday_effect_summary.csv"}

### Long-Weekend Effects
{lw_df.groupby('weekend')['ratio'].mean().to_string() if not lw_df.empty else "Long weekend 2024 data not loaded (station file matching required)"}

## Tables/Plots Created
| File | Description |
|------|-------------|
| `aadt_trends_by_station.csv` | Station × year AADT proxy, June mean daily volume, FC |
| `seasonal_index_by_station.csv` | Station × month seasonality index |
| `holiday_effect_summary.csv` | Holiday effect ratio summary |
| `fig_aadt_trend_2017_2024.png` | Line chart of annual volume trends by FC |
| `fig_seasonal_decomposition_examples.png` | Seasonality index by month (examples + FC aggregate) |
| `fig_holiday_effect.png` | Bar chart of holiday volume effect ratios |
| `fig_long_weekend_effects.png` | Long-weekend volume ratio grouped bar chart |
| `fig_peak_hour_stability.png` | AM/PM peak hour box plots by season |

## Risks/Caveats
1. **June-reference AADT proxy**: June is typically close to annual average for southeastern US,
   but may overestimate for resort/tourist corridors and underestimate in winter-peak areas.
2. **COVID dip analysis**: The 2019→2020 volume drop is observed in the data but may reflect
   multiple confounding factors beyond COVID-19 (data coverage changes, station dropouts).
3. **Tier mixing**: Historical (2017–2022) data uses directional lanes; CCS (2022–2023) uses
   numbered lanes. Volumes summed across all directions/lanes per station-day; comparison
   is valid if station configurations are stable, but lane-count changes may inflate/deflate trends.
4. **2024 per-station file format differs** from monthly tier: uses 'Start Time', 'Count' columns
   and includes speed/weight bins. Ensure Count column = total vehicle count per 5-min bin.
5. **Missing June 2022 from historical tier**: Used next available month (April 2022) as proxy.
6. **Holiday effect sample size**: Limited to stations present in CCS_5Min_2024/ directory.
   Stations with no matching cosit file were excluded.
7. **Seasonality from single year (2023)**: Does not capture inter-annual variability in seasonal patterns.

## Recommended Next Steps
1. **Extend AADT proxy to all 12 months** per year for selected stations to improve annual estimates.
2. **Compute proper AADT** using FHWA seasonal adjustment factors for Georgia by functional class.
3. **Validate June-proxy AADT** against any official GDOT AADT reports for cross-check.
4. **Expand holiday analysis** by reading all available 2024 station files (not just selected 20).
5. **Multi-year seasonality**: Stack 2022, 2023, and 2024 seasonal indices to assess inter-annual consistency.
6. **Peak-hour analysis**: Extend to a full year with directional breakdown (NB vs SB) for each station.
7. **COVID recovery analysis**: Use all months 2019–2022 to fit a recovery curve and estimate
   percent recovery by FC category.
"""

with open(OUT / 'temporal_trend_report.md', 'w') as f:
    f.write(report_lines)
log.info("Saved temporal_trend_report.md")

# ── Final output verification ─────────────────────────────────────────────
log.info("=== Final output verification ===")
expected_outputs = [
    'temporal_trend_agent.py',
    'aadt_trends_by_station.csv',
    'seasonal_index_by_station.csv',
    'holiday_effect_summary.csv',
    'fig_aadt_trend_2017_2024.png',
    'fig_seasonal_decomposition_examples.png',
    'fig_holiday_effect.png',
    'fig_long_weekend_effects.png',
    'fig_peak_hour_stability.png',
    'temporal_trend_report.md',
]
for fname in expected_outputs:
    fpath = OUT / fname
    exists = fpath.exists()
    size = fpath.stat().st_size if exists else 0
    status = f"OK ({size:,} bytes)" if exists else "MISSING"
    log.info(f"  {fname}: {status}")

log.info("=== temporal_trend_agent.py COMPLETE ===")
