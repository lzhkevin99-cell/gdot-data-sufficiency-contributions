"""
anomaly_representativeness_agent.py
Phase 3B: Anomaly Detection and Station Trustworthiness Scoring
GDOT EDA Workflow
"""

import os
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR       = "/Users/kevinli/Desktop/Research_Gtech_gdot"
RAW_DATA_DIR   = f"{BASE_DIR}/gdot_2025_data_total/CCS_5Min_2024"
OUT_DIR        = f"{BASE_DIR}/eda_output/anomalies"
os.makedirs(OUT_DIR, exist_ok=True)

DAILY_PROFILE  = f"{BASE_DIR}/eda_output/profiles/station_daily_volume_summary.csv"
ISSUE_TABLE    = f"{BASE_DIR}/eda_output/missingness/station_month_issue_table.csv"
SCORECARD      = f"{BASE_DIR}/eda_output/missingness/station_missingness_scorecard.csv"
MASTER_TABLE   = f"{BASE_DIR}/eda_output/inventory/station_master_table.csv"
EVENTS_FILE    = f"{BASE_DIR}/outputs/all_events_2024.csv"

print("=" * 70)
print("ANOMALY REPRESENTATIVENESS AGENT — Phase 3B")
print("=" * 70)

# ── Load reference tables ──────────────────────────────────────────────────────
print("\n[1] Loading reference tables...")

master    = pd.read_csv(MASTER_TABLE)
scorecard = pd.read_csv(SCORECARD)
issue_tbl = pd.read_csv(ISSUE_TABLE)
events    = pd.read_csv(EVENTS_FILE, parse_dates=['start', 'end'])

print(f"  master:    {len(master)} rows, cols: {list(master.columns)}")
print(f"  scorecard: {len(scorecard)} rows, cols: {list(scorecard.columns)}")
print(f"  issue_tbl: {len(issue_tbl)} rows, cols: {list(issue_tbl.columns)}")
print(f"  events:    {len(events)} rows, cols: {list(events.columns)}")

# Normalise cosit in events to integer for joining
events['cosit_int'] = events['cosit'].apply(
    lambda x: int(str(x).lstrip('0') or '0') if pd.notna(x) else np.nan
)

# ── Task 1: Select 60 stations ─────────────────────────────────────────────────
print("\n[2] Selecting 60 stations for raw-data anomaly detection...")

# Merge master with scorecard
merged = master.merge(scorecard[['station_id', 'pct_complete', 'missingness_rate', 'outage_style']],
                      on='station_id', how='left')

# Filter: in_5min_2024 == True AND pct_complete > 0.7
eligible = merged[(merged['in_5min_2024'] == True) &
                  (merged['pct_complete'] > 0.7) &
                  (merged['cosit'].notna())].copy()

print(f"  Eligible stations: {len(eligible)}")

# Stratified sample across functional classes
fc_counts = eligible['functional_class'].value_counts()
print(f"  FC distribution:\n{fc_counts.to_string()}")

TOTAL_SAMPLE = 60
fc_weights   = fc_counts / fc_counts.sum()
fc_alloc     = (fc_weights * TOTAL_SAMPLE).round().astype(int)
# Adjust rounding to sum to 60
diff = TOTAL_SAMPLE - fc_alloc.sum()
fc_alloc.iloc[0] += diff

sampled_list = []
for fc, n in fc_alloc.items():
    pool = eligible[eligible['functional_class'] == fc]
    k    = min(n, len(pool))
    sampled_list.append(pool.sample(n=k, random_state=42))

sampled = pd.concat(sampled_list, ignore_index=True).drop_duplicates('station_id')
if len(sampled) < TOTAL_SAMPLE:
    # Top-up from remaining eligible stations
    remaining = eligible[~eligible['station_id'].isin(sampled['station_id'])]
    topup = remaining.sample(n=min(TOTAL_SAMPLE - len(sampled), len(remaining)), random_state=42)
    sampled = pd.concat([sampled, topup], ignore_index=True)

sampled = sampled.head(TOTAL_SAMPLE)
print(f"  Final sample size: {len(sampled)} stations")

# ── Task 1: Read raw data & detect anomalies ───────────────────────────────────
print("\n[3] Reading raw 5-min data and detecting anomalies...")

anomaly_records = []
station_daily_vols = {}  # station_id -> DataFrame with date, daily_volume

def cosit_to_folder(cosit):
    return str(int(cosit)).zfill(12)

def read_station_daily(cosit, station_id):
    """Read data-1.csv for a station, return daily totals."""
    folder_id = cosit_to_folder(cosit)
    fpath = f"{RAW_DATA_DIR}/GDOT_CCS-{folder_id}-data-1.csv"
    if not os.path.exists(fpath):
        return None
    try:
        df = pd.read_csv(fpath, parse_dates=['Start Time'])
        df.columns = df.columns.str.strip()
        df = df.rename(columns={'Start Time': 'start_time', 'Coverage %': 'coverage_pct', 'Count': 'count'})
        # Filter to 2024
        df = df[df['start_time'].dt.year == 2024]
        # Filter coverage >= 50%
        df = df[df['coverage_pct'] >= 50]
        if df.empty:
            return None
        df['date'] = df['start_time'].dt.date
        daily = df.groupby('date')['count'].sum().reset_index()
        daily.columns = ['date', 'daily_volume']
        daily['station_id'] = station_id
        return daily
    except Exception as e:
        print(f"    ERROR reading {fpath}: {e}")
        return None

total_anomaly_days = 0
stations_with_data = 0

for _, row in sampled.iterrows():
    sid    = row['station_id']
    cosit  = row['cosit']

    daily = read_station_daily(cosit, sid)
    if daily is None or len(daily) < 10:
        continue

    stations_with_data += 1

    # Station-level stats
    med = daily['daily_volume'].median()
    q25 = daily['daily_volume'].quantile(0.25)
    q75 = daily['daily_volume'].quantile(0.75)
    iqr = q75 - q25

    lo_thresh = med - 3 * iqr
    hi_thresh = med + 3 * iqr
    low_vol_thresh = 0.1 * med if med > 0 else 0

    daily['median_volume'] = med
    daily['iqr'] = iqr
    daily['anomaly_iqr'] = (daily['daily_volume'] < lo_thresh) | (daily['daily_volume'] > hi_thresh)
    daily['anomaly_lowvol'] = (daily['daily_volume'] < low_vol_thresh) & (daily['daily_volume'] >= 0)
    daily['is_anomaly'] = daily['anomaly_iqr'] | daily['anomaly_lowvol']

    station_daily_vols[sid] = daily.copy()

    # Build anomaly type
    anom_days = daily[daily['is_anomaly']].copy()
    total_anomaly_days += len(anom_days)

    for _, aday in anom_days.iterrows():
        atype = []
        if aday['anomaly_iqr']:
            if aday['daily_volume'] < lo_thresh:
                atype.append('IQR_LOW')
            else:
                atype.append('IQR_HIGH')
        if aday['anomaly_lowvol']:
            atype.append('LOW_VOL')

        anomaly_records.append({
            'station_id': sid,
            'cosit': int(cosit),
            'date': aday['date'],
            'daily_volume': aday['daily_volume'],
            'median_volume': med,
            'iqr': iqr,
            'anomaly_type': '|'.join(atype),
            'event_flag': None,
            'event_description': None,
            'explained': None
        })

print(f"  Stations with readable data: {stations_with_data}")
print(f"  Total raw anomaly days detected: {total_anomaly_days}")

# ── Task 2: Cross-check with event flags ──────────────────────────────────────
print("\n[4] Cross-checking anomalies with event flags...")

EXPLAIN_FLAGS = ['Holiday', 'Volume Bad', 'Volume Outlier', 'Volume Atypical',
                 'Roadworks', 'Road Closure', 'Accident']

# Build event lookup: cosit_int -> list of (start_date, end_date, flag, desc)
event_lookup = {}
for _, ev in events.iterrows():
    c = ev['cosit_int']
    if pd.isna(c):
        continue
    c = int(c)
    if c not in event_lookup:
        event_lookup[c] = []
    event_lookup[c].append({
        'start': ev['start'],
        'end': ev['end'],
        'flag': ev['flag'],
        'desc': ev.get('description', '')
    })

def check_event(cosit_int, check_date):
    """Return (matched_flag, desc) or (None, None)."""
    if cosit_int not in event_lookup:
        return None, None
    check_dt_start = pd.Timestamp(check_date)
    check_dt_end   = check_dt_start + pd.Timedelta(days=1)
    for ev in event_lookup[cosit_int]:
        if ev['flag'] not in EXPLAIN_FLAGS:
            continue
        # Overlap check: event overlaps the day
        if ev['start'] < check_dt_end and ev['end'] > check_dt_start:
            return ev['flag'], ev['desc']
    return None, None

explained_count   = 0
unexplained_count = 0

for rec in anomaly_records:
    eflag, edesc = check_event(rec['cosit'], rec['date'])
    rec['event_flag']        = eflag
    rec['event_description'] = edesc
    rec['explained']         = (eflag is not None)
    if rec['explained']:
        explained_count += 1
    else:
        unexplained_count += 1

print(f"  Explained anomalies:   {explained_count}")
print(f"  Unexplained anomalies: {unexplained_count}")

# Save anomaly log
anomaly_log = pd.DataFrame(anomaly_records)
if not anomaly_log.empty:
    anomaly_log['year']  = pd.to_datetime(anomaly_log['date']).dt.year
    anomaly_log['month'] = pd.to_datetime(anomaly_log['date']).dt.month
anomaly_log.to_csv(f"{OUT_DIR}/anomaly_log.csv", index=False)
print(f"  Saved anomaly_log.csv ({len(anomaly_log)} rows)")

# ── Task 3: Station-month trustworthiness scoring ─────────────────────────────
print("\n[5] Scoring station-month trustworthiness...")

# Build anomaly summary per station-month
if not anomaly_log.empty:
    anom_sm = anomaly_log.groupby(['station_id', 'year', 'month']).agg(
        n_anomaly_days=('date', 'count'),
        n_unexplained_anomalies=('explained', lambda x: (~x).sum())
    ).reset_index()
else:
    anom_sm = pd.DataFrame(columns=['station_id', 'year', 'month',
                                    'n_anomaly_days', 'n_unexplained_anomalies'])

sampled_stations = set(sampled['station_id'])
raw_data_stations = set(station_daily_vols.keys())

# Merge issue table with anomaly summary
tm = issue_tbl.merge(anom_sm, on=['station_id', 'year', 'month'], how='left')
tm['n_anomaly_days']          = tm['n_anomaly_days'].fillna(0).astype(int)
tm['n_unexplained_anomalies'] = tm['n_unexplained_anomalies'].fillna(0).astype(int)

def assign_trust_tier(row):
    """Assign trust tier. Uses raw_data if we read it, else coverage_proxy."""
    sid = row['station_id']
    if sid in raw_data_stations:
        # Raw data method
        cov  = row['coverage_pct']
        unex = row['n_unexplained_anomalies']
        if cov >= 85 and unex == 0:
            return 'TRUSTED', 'raw_data'
        elif (cov >= 50 and unex <= 2) or (cov >= 85 and 1 <= unex <= 2):
            return 'CAUTION', 'raw_data'
        else:
            return 'EXCLUDE', 'raw_data'
    else:
        # Coverage proxy method
        qf = row['quality_flag']
        if qf == 'COMPLETE':
            return 'TRUSTED', 'coverage_proxy'
        elif qf in ['PARTIAL_MINOR', 'PARTIAL_MAJOR']:
            return 'CAUTION', 'coverage_proxy'
        else:  # SPARSE, ABSENT, or unknown
            return 'EXCLUDE', 'coverage_proxy'

tiers   = tm.apply(assign_trust_tier, axis=1)
tm['trust_tier'] = [t[0] for t in tiers]
tm['method']     = [t[1] for t in tiers]

trust_counts = tm['trust_tier'].value_counts()
print(f"  Trust tier distribution:\n{trust_counts.to_string()}")

tm.to_csv(f"{OUT_DIR}/station_month_trustworthiness.csv", index=False)
print(f"  Saved station_month_trustworthiness.csv ({len(tm)} rows)")

# ── Task 4: Station-level trust summary ───────────────────────────────────────
print("\n[6] Building station-level trust summary...")

st_agg = tm.groupby('station_id').agg(
    n_trusted_months=('trust_tier', lambda x: (x == 'TRUSTED').sum()),
    n_caution_months=('trust_tier', lambda x: (x == 'CAUTION').sum()),
    n_exclude_months=('trust_tier', lambda x: (x == 'EXCLUDE').sum()),
).reset_index()

st_agg['total_months'] = (st_agg['n_trusted_months'] + st_agg['n_caution_months'] +
                           st_agg['n_exclude_months'])
st_agg['pct_trusted'] = np.where(
    st_agg['total_months'] > 0,
    st_agg['n_trusted_months'] / st_agg['total_months'],
    0.0
)

def station_tier(row):
    p = row['pct_trusted']
    if p >= 0.8:
        return 'HIGH'
    elif p >= 0.5:
        return 'MODERATE'
    else:
        return 'LOW'

st_agg['station_trust_tier'] = st_agg.apply(station_tier, axis=1)

# Join with master for FC info
st_agg = st_agg.merge(
    master[['station_id', 'cosit', 'functional_class', 'fc_urban_rural', 'n_sources', 'complete_months']],
    on='station_id', how='left'
)

st_agg.to_csv(f"{OUT_DIR}/station_trust_summary.csv", index=False)
print(f"  Saved station_trust_summary.csv ({len(st_agg)} rows)")
print(f"  Station trust tier distribution:\n{st_agg['station_trust_tier'].value_counts().to_string()}")

# ── Task 5: Trusted / Caution / Excluded station lists ───────────────────────
print("\n[7] Building trusted/caution/excluded station lists...")

trusted_mask = (
    (st_agg['station_trust_tier'] == 'HIGH') &
    (st_agg['n_sources'] >= 2) &
    (st_agg['n_trusted_months'] >= 8)
)
trusted_stations = st_agg[trusted_mask].copy()

excluded_mask = (
    (st_agg['station_trust_tier'] == 'LOW') |
    (st_agg['n_trusted_months'] < 3)
)
excluded_stations = st_agg[excluded_mask].copy()

caution_mask = ~trusted_mask & ~excluded_mask
caution_stations = st_agg[caution_mask].copy()

trusted_stations.to_csv(f"{OUT_DIR}/trusted_station_list.csv", index=False)
caution_stations.to_csv(f"{OUT_DIR}/caution_station_list.csv", index=False)
excluded_stations.to_csv(f"{OUT_DIR}/excluded_station_list.csv", index=False)

print(f"  TRUSTED stations:  {len(trusted_stations)}")
print(f"  CAUTION stations:  {len(caution_stations)}")
print(f"  EXCLUDED stations: {len(excluded_stations)}")

# ── Task 6: Plots ──────────────────────────────────────────────────────────────
print("\n[8] Generating plots...")

# Helper: map FC to short label
def fc_short(fc):
    m = re.match(r'(\d+):', str(fc))
    return f"FC{m.group(1)}" if m else str(fc)[:8]

# ── Plot 1: Stacked bar — trust tiers by functional class ─────────────────────
fig1, ax1 = plt.subplots(figsize=(10, 6))

fc_trust = tm.merge(master[['station_id', 'functional_class']], on='station_id', how='left')
fc_trust['fc_short'] = fc_trust['functional_class'].apply(fc_short)

pivot = fc_trust.groupby(['fc_short', 'trust_tier']).size().unstack(fill_value=0)
for col in ['TRUSTED', 'CAUTION', 'EXCLUDE']:
    if col not in pivot.columns:
        pivot[col] = 0
pivot = pivot[['TRUSTED', 'CAUTION', 'EXCLUDE']]
pivot = pivot.sort_index()

colors = {'TRUSTED': '#2ecc71', 'CAUTION': '#f39c12', 'EXCLUDE': '#e74c3c'}
bottom = np.zeros(len(pivot))
for tier in ['TRUSTED', 'CAUTION', 'EXCLUDE']:
    vals = pivot[tier].values
    ax1.bar(pivot.index, vals, bottom=bottom, color=colors[tier], label=tier, alpha=0.85)
    bottom += vals

ax1.set_xlabel('Functional Class', fontsize=12)
ax1.set_ylabel('Number of Station-Months', fontsize=12)
ax1.set_title('Trust Tier Distribution by Functional Class', fontsize=14)
ax1.legend(title='Trust Tier')
ax1.tick_params(axis='x', rotation=30)
plt.tight_layout()
fig1.savefig(f"{OUT_DIR}/fig_trust_tier_distribution.png", dpi=150)
plt.close(fig1)
print("  Saved fig_trust_tier_distribution.png")

# ── Plot 2: Anomaly timeline for 4 example stations ───────────────────────────
# Pick 1 station per major FC that has raw data
major_fcs = ['1: Interstate', '2: Principal Arterial - Other Freeway & Expressway',
             '4: Minor Arterial', '6: Minor Collector']

example_stations = []
fc_checked = set()
for fc in major_fcs:
    pool = sampled[sampled['functional_class'] == fc]
    for _, row in pool.iterrows():
        if row['station_id'] in raw_data_stations:
            example_stations.append(row)
            fc_checked.add(fc)
            break

# If fewer than 4, fill from any FC with raw data
if len(example_stations) < 4:
    for _, row in sampled.iterrows():
        if len(example_stations) >= 4:
            break
        if row['station_id'] in raw_data_stations and row['station_id'] not in [e['station_id'] for e in example_stations]:
            example_stations.append(row)

example_stations = example_stations[:4]

fig2, axes2 = plt.subplots(4, 1, figsize=(14, 16))
for i, erow in enumerate(example_stations):
    ax = axes2[i]
    sid = erow['station_id']
    cosit_val = int(erow['cosit'])
    dv = station_daily_vols.get(sid)
    if dv is None or dv.empty:
        ax.text(0.5, 0.5, f"{sid}: no data", ha='center', va='center', transform=ax.transAxes)
        continue

    dv = dv.copy()
    dv['date_ts'] = pd.to_datetime(dv['date'])

    ax.plot(dv['date_ts'], dv['daily_volume'], color='steelblue', linewidth=0.8, alpha=0.7, label='Daily Volume')

    # Mark anomaly days
    anom = dv[dv['is_anomaly']]
    ax.scatter(anom['date_ts'], anom['daily_volume'], color='red', s=20, zorder=5, label='Anomaly')

    # Mark event days (any event for this station)
    if cosit_val in event_lookup:
        for ev in event_lookup[cosit_val]:
            if ev['flag'] in EXPLAIN_FLAGS:
                ev_date = ev['start'].date()
                match_days = dv[dv['date'] == ev_date]
                if not match_days.empty:
                    ax.scatter(match_days['date_ts'], match_days['daily_volume'],
                               color='orange', s=30, zorder=6, marker='^', label='Event')

    # Threshold lines
    med = dv['median_volume'].iloc[0]
    iqr_val = dv['iqr'].iloc[0]
    ax.axhline(med, color='green', linestyle='--', linewidth=0.8, alpha=0.6, label='Median')
    ax.axhline(med - 3 * iqr_val, color='red', linestyle=':', linewidth=0.8, alpha=0.5, label='3-IQR thresh')
    ax.axhline(med + 3 * iqr_val, color='red', linestyle=':', linewidth=0.8, alpha=0.5)

    fc_label = str(erow.get('functional_class', ''))[:25]
    ax.set_title(f"Station {sid} | {fc_label}", fontsize=10)
    ax.set_ylabel('Daily Volume', fontsize=9)
    ax.set_xlabel('')

    # De-duplicate legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), fontsize=7, loc='upper right')

plt.suptitle('Daily Volume with Anomaly Days — 4 Example Stations', fontsize=13, y=1.01)
plt.tight_layout()
fig2.savefig(f"{OUT_DIR}/fig_anomaly_timeline.png", dpi=150, bbox_inches='tight')
plt.close(fig2)
print("  Saved fig_anomaly_timeline.png")

# ── Plot 3: Volume histograms with thresholds — 2×2 grid ──────────────────────
fig3, axes3 = plt.subplots(2, 2, figsize=(12, 10))
axes3_flat = axes3.flatten()

for i, erow in enumerate(example_stations[:4]):
    ax = axes3_flat[i]
    sid = erow['station_id']
    dv = station_daily_vols.get(sid)
    if dv is None or dv.empty:
        ax.text(0.5, 0.5, f"{sid}: no data", ha='center', va='center', transform=ax.transAxes)
        continue

    vols = dv['daily_volume'].values
    med  = np.median(vols)
    q25  = np.percentile(vols, 25)
    q75  = np.percentile(vols, 75)
    iqr_val = q75 - q25

    ax.hist(vols, bins=40, color='steelblue', alpha=0.7, edgecolor='white')
    ax.axvline(med, color='green', linestyle='--', linewidth=1.5, label=f'Median: {med:,.0f}')
    ax.axvline(med - 3 * iqr_val, color='red', linestyle=':', linewidth=1.5, label=f'Low thresh: {med - 3*iqr_val:,.0f}')
    ax.axvline(med + 3 * iqr_val, color='darkred', linestyle=':', linewidth=1.5, label=f'High thresh: {med + 3*iqr_val:,.0f}')
    ax.axvline(0.1 * med, color='orange', linestyle='-.', linewidth=1.2, label=f'Low-vol: {0.1*med:,.0f}')

    n_anom = dv['is_anomaly'].sum()
    fc_label = str(erow.get('functional_class', ''))[:20]
    ax.set_title(f"{sid} | {fc_label}\n({n_anom} anomaly days)", fontsize=9)
    ax.set_xlabel('Daily Volume', fontsize=8)
    ax.set_ylabel('Frequency', fontsize=8)
    ax.legend(fontsize=7)

plt.suptitle('Daily Volume Distributions with Anomaly Thresholds', fontsize=13)
plt.tight_layout()
fig3.savefig(f"{OUT_DIR}/fig_volume_anomaly_examples.png", dpi=150)
plt.close(fig3)
print("  Saved fig_volume_anomaly_examples.png")

# ── Task 7: Write report ───────────────────────────────────────────────────────
print("\n[9] Writing anomaly_representativeness_report.md...")

n_total_stations   = len(master)
n_sampled          = len(sampled)
n_with_raw         = stations_with_data
n_anom_total       = len(anomaly_log)
n_explained        = explained_count
n_unexplained      = unexplained_count
pct_explained      = 100.0 * n_explained / n_anom_total if n_anom_total > 0 else 0.0

n_trusted_sm  = (tm['trust_tier'] == 'TRUSTED').sum()
n_caution_sm  = (tm['trust_tier'] == 'CAUTION').sum()
n_exclude_sm  = (tm['trust_tier'] == 'EXCLUDE').sum()
n_total_sm    = len(tm)

n_trusted_st  = len(trusted_stations)
n_caution_st  = len(caution_stations)
n_excluded_st = len(excluded_stations)

report = f"""## Objective

Detect anomalous daily volumes at 2024 GDOT traffic count stations, cross-check detected anomalies against known event flags, and assign trustworthiness tiers to each station-month and station. Outputs support downstream decisions about which station-months are suitable for traffic modeling.

## Methods

### Station Selection (Task 1)
- Universe: {n_total_stations} stations in station_master_table.
- Eligibility criteria: in_5min_2024 == True AND pct_complete > 0.70 (from missingness scorecard).
- Stratified sample of {n_sampled} stations across functional classes, proportional to FC representation.
- {n_with_raw} of the {n_sampled} sampled stations had readable raw 5-min data files.

### Anomaly Detection (Task 1)
For each station with raw data:
- Aggregated 5-min intervals to daily totals, filtering intervals with Coverage % < 50.
- Computed station-level median and IQR (Q75 - Q25) over all observed days.
- Flagged anomaly days using two criteria:
  1. IQR rule: daily_volume < (median − 3×IQR) OR > (median + 3×IQR)
  2. Low-volume rule: daily_volume < 10% of median (consistent with potential sensor dropout when coverage is otherwise high)

### Event Cross-Check (Task 2)
- Loaded {len(events)} event flags from all_events_2024.csv.
- Matched flagged anomaly days to events of type: Holiday, Volume Bad, Volume Outlier, Volume Atypical, Roadworks, Road Closure, Accident.
- Classification: EXPLAINED (overlap found) vs UNEXPLAINED (no matching event).

### Trustworthiness Scoring (Task 3)
- For the {n_with_raw} stations with raw data: used coverage_pct + unexplained anomaly count to assign TRUSTED / CAUTION / EXCLUDE per station-month.
- For remaining stations: used quality_flag from station_month_issue_table as proxy (COMPLETE → TRUSTED; PARTIAL_MINOR / PARTIAL_MAJOR → CAUTION; SPARSE / ABSENT → EXCLUDE).

### Station Aggregation (Tasks 4–5)
- Summarised station-month tiers into pct_trusted per station → HIGH / MODERATE / LOW station trust tier.
- Applied additional criteria for station lists: n_sources ≥ 2 and n_trusted_months ≥ 8 for TRUSTED list; n_trusted_months < 3 or tier == LOW for EXCLUDED list.

## Key Findings

### Anomaly Detection
- Total anomaly-days detected across {n_with_raw} stations: **{n_anom_total}**
- Explained by event flags: **{n_explained}** ({pct_explained:.1f}%)
- Unexplained anomaly-days: **{n_unexplained}** ({100 - pct_explained:.1f}%)
- Note: "Unexplained" does not imply the data is wrong — it means no corresponding event flag exists in the available event log. Zero-volume overnight periods at rural stations are not flagged because the IQR-based method naturally accommodates station-typical patterns.

### Station-Month Trustworthiness
| Tier    | Station-Months | % of Total |
|---------|---------------|------------|
| TRUSTED | {n_trusted_sm:>13,} | {100*n_trusted_sm/n_total_sm:.1f}% |
| CAUTION | {n_caution_sm:>13,} | {100*n_caution_sm/n_total_sm:.1f}% |
| EXCLUDE | {n_exclude_sm:>13,} | {100*n_exclude_sm/n_total_sm:.1f}% |
| **Total** | {n_total_sm:>13,} | 100.0% |

### Station-Level Trust Summary
| Tier     | Stations |
|----------|----------|
| TRUSTED  | {n_trusted_st:>8} |
| CAUTION  | {n_caution_st:>8} |
| EXCLUDED | {n_excluded_st:>8} |

## Tables/Plots Created

| File | Description |
|------|-------------|
| `anomaly_log.csv` | Per-anomaly-day record: station, date, volume, thresholds, event flag, explained flag |
| `station_month_trustworthiness.csv` | Per station-month: coverage, quality flag, anomaly counts, trust tier, method |
| `station_trust_summary.csv` | Per station: n trusted/caution/exclude months, pct_trusted, station trust tier |
| `trusted_station_list.csv` | {n_trusted_st} stations rated HIGH trust with ≥2 sources and ≥8 trusted months |
| `caution_station_list.csv` | {n_caution_st} stations suitable for use with caveats |
| `excluded_station_list.csv` | {n_excluded_st} stations flagged for investigation or exclusion |
| `fig_trust_tier_distribution.png` | Stacked bar chart of station-month trust tiers by functional class |
| `fig_anomaly_timeline.png` | Daily volume time series for 4 example stations with anomaly and event markers |
| `fig_volume_anomaly_examples.png` | 2×2 histogram grid with IQR and low-volume thresholds |

## Risks/Caveats

1. **Coverage proxy limitation**: The majority of stations were scored using quality_flag (coverage proxy) rather than raw data inspection. The proxy cannot detect volume-level anomalies — only data presence.
2. **IQR sensitivity**: The 3×IQR rule is robust but may miss sustained gradual drift. Stations with highly variable demand (e.g., near event venues) may have inflated IQR, reducing anomaly detection sensitivity.
3. **Unexplained anomalies**: {n_unexplained} anomaly-days have no event flag. These may reflect: (a) genuine sensor issues, (b) events not recorded in the event log, (c) legitimate unusual traffic (e.g., incidents not captured, detours). These are not classified as erroneous without further investigation.
4. **Low-volume rule**: Flagging days with volume < 10% of median as "consistent with sensor failure" is heuristic. For rural overnight stations, median may already be near zero — the per-station threshold mitigates this but does not eliminate it.
5. **Sample size**: Only {n_with_raw} stations had raw data read. Stations not in the sample rely on the coverage proxy, which may underestimate anomaly risk.
6. **Single-direction data**: data-1.csv captures one primary direction; multi-directional anomalies may be missed.

## Recommended Next Steps

1. **Investigate unexplained anomalies**: Pull the {n_unexplained} unexplained anomaly-days and audit against maintenance logs, weather records, and construction permit databases.
2. **Expand raw-data coverage**: Run the IQR anomaly check on all in_5min_2024 stations (not just the 60-station sample) to reduce reliance on the coverage proxy.
3. **Refine the low-volume threshold**: Consider a tiered threshold (e.g., 5% for rural, 15% for urban interstate) to reduce false positives at low-volume rural sites.
4. **Cross-validate with Phase 3A profiles**: Compare anomaly-day volumes with the F-class distribution profiles from Phase 3A to determine whether anomaly days skew toward atypical vehicle mixes.
5. **Flag CAUTION stations for sensitivity testing**: In downstream modeling, run models with and without CAUTION-tier station-months to quantify their influence on estimates.
6. **Revisit EXCLUDED stations**: Some may be recoverable with partial-month data after dropping specific anomaly intervals.
"""

with open(f"{OUT_DIR}/anomaly_representativeness_report.md", 'w') as f:
    f.write(report)
print("  Saved anomaly_representativeness_report.md")

# ── Final summary ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE 3B COMPLETE — Output files:")
for fname in [
    "anomaly_log.csv",
    "station_month_trustworthiness.csv",
    "station_trust_summary.csv",
    "trusted_station_list.csv",
    "caution_station_list.csv",
    "excluded_station_list.csv",
    "fig_trust_tier_distribution.png",
    "fig_anomaly_timeline.png",
    "fig_volume_anomaly_examples.png",
    "anomaly_representativeness_report.md",
]:
    fpath = f"{OUT_DIR}/{fname}"
    size  = os.path.getsize(fpath) if os.path.exists(fpath) else 0
    print(f"  {'OK' if size > 0 else 'MISSING':6s}  {fname}  ({size:,} bytes)")
print("=" * 70)
