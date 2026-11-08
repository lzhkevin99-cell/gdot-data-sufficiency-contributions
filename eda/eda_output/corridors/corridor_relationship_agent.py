"""
corridor_relationship_agent.py
Phase 3A: Inter-station correlations, corridor clustering, reference station identification
GDOT EDA Workflow
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR     = "/Users/kevinli/Desktop/Research_Gtech_gdot"
RAW_DIR      = os.path.join(BASE_DIR, "gdot_2025_data_total", "CCS_5Min_2024")
EDA_DIR      = os.path.join(BASE_DIR, "eda_output")
OUT_DIR      = os.path.join(EDA_DIR, "corridors")
os.makedirs(OUT_DIR, exist_ok=True)

MASTER_CSV      = os.path.join(EDA_DIR, "inventory",   "station_master_table.csv")
SCORECARD_CSV   = os.path.join(EDA_DIR, "missingness", "station_missingness_scorecard.csv")
DAILY_SUMM_CSV  = os.path.join(EDA_DIR, "profiles",    "station_daily_volume_summary.csv")

MIN_OVERLAP_DAYS = 180
TOP_N_STATIONS   = 80
CLUSTER_DIST_THR = 0.15   # r > 0.85
BEH_NEIGHBOR_R   = 0.70
BEH_NEIGHBOR_KM  = 50.0
K_NEIGHBORS      = 5

print("=" * 70)
print("corridor_relationship_agent.py  —  started", datetime.now())
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════════
# Task 1 — Build daily volume time-series matrix
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 1] Building daily volume matrix …")

master = pd.read_csv(MASTER_CSV)
scorecard = pd.read_csv(SCORECARD_CSV)
daily_summ = pd.read_csv(DAILY_SUMM_CSV)

print(f"  master: {len(master)} rows | scorecard: {len(scorecard)} rows | daily_summ: {len(daily_summ)} rows")
print(f"  master columns: {list(master.columns)}")
print(f"  scorecard columns: {list(scorecard.columns)}")
print(f"  daily_summ columns: {list(daily_summ.columns)}")

# Filter master: in_5min_2024 == True, n_sources >= 2
master['in_5min_2024'] = master['in_5min_2024'].astype(str).str.lower().isin(['true', '1', 'yes'])
master_filt = master[master['in_5min_2024'] & (master['n_sources'] >= 2)].copy()
print(f"  Stations with in_5min_2024=True and n_sources>=2: {len(master_filt)}")

# Merge with scorecard to get pct_complete
master_filt = master_filt.merge(
    scorecard[['station_id', 'pct_complete', 'missingness_rate', 'outage_style']],
    on='station_id', how='left'
)

# Select top N by pct_complete
top_stations = (
    master_filt
    .sort_values('pct_complete', ascending=False)
    .head(TOP_N_STATIONS)
    .reset_index(drop=True)
)
print(f"  Top {TOP_N_STATIONS} stations selected (by pct_complete)")

# Check if daily_summ has per-day data (look for date-like columns)
date_cols = [c for c in daily_summ.columns if c not in [
    'station_id','functional_class','fc_urban_rural','pct_complete','n_days',
    'median_daily_volume','mean_daily_volume','p10_daily','p90_daily',
    'weekday_median','weekend_median','weekday_weekend_ratio',
    'am_peak_hour','pm_peak_hour','pct_heavy'
] and not c.startswith('F') and not c.endswith('_frac')]
print(f"  Per-day columns in daily_summ: {len(date_cols)} → building from raw data")

# ── Build from raw 5-min data ──────────────────────────────────────────────────
def cosit_to_folder(cosit):
    """Convert integer cosit to zero-padded 12-digit folder name."""
    return str(int(cosit)).zfill(12)

def read_daily_volume(cosit, station_id):
    """Read raw data-1.csv for a station; return Series of daily sums."""
    folder = cosit_to_folder(cosit)
    fpath = os.path.join(RAW_DIR, f"GDOT_CCS-{folder}-data-1.csv")
    if not os.path.exists(fpath):
        return None
    try:
        df = pd.read_csv(
            fpath,
            usecols=['Start Time', 'Coverage %', 'Count'],
            parse_dates=['Start Time'],
            infer_datetime_format=True,
            low_memory=True
        )
        df = df[df['Coverage %'] >= 50].copy()
        df['date'] = df['Start Time'].dt.date
        daily = df.groupby('date')['Count'].sum()
        daily.name = station_id
        return daily
    except Exception as e:
        print(f"    WARNING: could not read {fpath}: {e}")
        return None

# Collect daily series
all_series = []
n_read = 0
n_missing = 0
for _, row in top_stations.iterrows():
    cosit = row['cosit']
    sid   = row['station_id']
    s = read_daily_volume(cosit, sid)
    if s is not None and len(s) > 0:
        all_series.append(s)
        n_read += 1
    else:
        n_missing += 1
    if n_read % 10 == 0 and n_read > 0:
        print(f"    … read {n_read}/{len(top_stations)} stations", end='\r', flush=True)

print(f"\n  Successfully read {n_read} station files; {n_missing} not found/empty")

# Build matrix
daily_matrix = pd.DataFrame(all_series).T
daily_matrix.index = pd.to_datetime(daily_matrix.index)
daily_matrix = daily_matrix.sort_index()

# Filter to 2024
daily_matrix = daily_matrix[
    (daily_matrix.index >= '2024-01-01') & (daily_matrix.index <= '2024-12-31')
]

print(f"  Daily volume matrix: {daily_matrix.shape[0]} dates × {daily_matrix.shape[1]} stations")
print(f"  Date range: {daily_matrix.index.min()} – {daily_matrix.index.max()}")
print(f"  Mean non-null per station: {daily_matrix.notna().sum().mean():.1f} days")

# ══════════════════════════════════════════════════════════════════════════════
# Task 2 — Pairwise Pearson correlation
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 2] Computing pairwise Pearson correlations …")

corr_matrix = daily_matrix.corr(method='pearson', min_periods=MIN_OVERLAP_DAYS)

# How many valid pairs?
n_stations_corr = corr_matrix.shape[0]
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
all_r = upper.stack().dropna()
n_valid_pairs = len(all_r)

print(f"  Stations with any valid correlation: {n_stations_corr}")
print(f"  Valid station pairs (≥{MIN_OVERLAP_DAYS} overlap days): {n_valid_pairs}")
print(f"  r stats → mean={all_r.mean():.3f}, median={all_r.median():.3f}, "
      f"min={all_r.min():.3f}, max={all_r.max():.3f}")
print(f"  Pairs with r > 0.85: {(all_r > 0.85).sum()} ({(all_r > 0.85).mean()*100:.1f}%)")

# Save correlation matrix
corr_out = os.path.join(OUT_DIR, "pairwise_correlation_matrix.csv")
corr_matrix.to_csv(corr_out)
print(f"  Saved: {corr_out}")

# Distribution plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(all_r.values, bins=50, color='steelblue', edgecolor='white', alpha=0.85)
ax.axvline(all_r.mean(), color='red', ls='--', lw=1.5, label=f'Mean = {all_r.mean():.3f}')
ax.axvline(0.85, color='orange', ls=':', lw=1.5, label='r = 0.85 threshold')
ax.set_xlabel("Pearson r", fontsize=12)
ax.set_ylabel("Number of station pairs", fontsize=12)
ax.set_title(f"Distribution of Pairwise Pearson r\n"
             f"({n_valid_pairs:,} valid pairs from {n_stations_corr} stations)", fontsize=12)
ax.legend()
plt.tight_layout()
fig_dist = os.path.join(OUT_DIR, "fig_correlation_distribution.png")
plt.savefig(fig_dist, dpi=150)
plt.close()
print(f"  Saved: {fig_dist}")

# ══════════════════════════════════════════════════════════════════════════════
# Task 3 — Hierarchical clustering and heatmap
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 3] Hierarchical clustering …")

# Drop stations that have NO valid correlation with any other
valid_stations = corr_matrix.index[corr_matrix.notna().sum(axis=1) > 1].tolist()
corr_sub = corr_matrix.loc[valid_stations, valid_stations].copy()

# Fill NaN with 0 for distance computation only (not for saving)
corr_filled = corr_sub.fillna(0)

# Clamp to [-1, 1] to avoid numerical issues
corr_filled = corr_filled.clip(-1, 1)

# Distance matrix: 1 - r
dist_mat = 1 - corr_filled
np.fill_diagonal(dist_mat.values, 0)
dist_mat = dist_mat.clip(0, 2)

n_clust_stations = len(valid_stations)
print(f"  Stations used for clustering: {n_clust_stations}")

if n_clust_stations < 2:
    print("  WARNING: fewer than 2 stations with valid correlations — skipping clustering")
    linkage_mat = None
    labels_ordered = valid_stations
else:
    # Convert to condensed distance vector
    dist_condensed = squareform(dist_mat.values, checks=False)
    dist_condensed = np.clip(dist_condensed, 0, None)

    linkage_mat = linkage(dist_condensed, method='average')

    # Cluster assignments with distance threshold 0.15 → r > 0.85
    cluster_ids = fcluster(linkage_mat, t=CLUSTER_DIST_THR, criterion='distance')
    cluster_series = pd.Series(cluster_ids, index=valid_stations, name='cluster_id')

    # Reorder by cluster
    ordered_idx = pd.DataFrame({
        'station_id': valid_stations,
        'cluster_id': cluster_ids
    }).sort_values('cluster_id')['station_id'].tolist()

    # Heatmap
    corr_ordered = corr_sub.loc[ordered_idx, ordered_idx]
    mask = corr_ordered.isna()

    fig_h, ax_h = plt.subplots(figsize=(max(10, n_clust_stations // 3),
                                         max(8,  n_clust_stations // 3)))
    sns.heatmap(
        corr_ordered,
        mask=mask,
        cmap='RdYlGn',
        vmin=-1, vmax=1,
        center=0,
        square=True,
        linewidths=0,
        cbar_kws={'label': 'Pearson r', 'shrink': 0.6},
        xticklabels=False,
        yticklabels=False,
        ax=ax_h
    )
    ax_h.set_title(f"Inter-Station Correlation Matrix (clustered)\n"
                   f"{n_clust_stations} stations, average linkage, threshold r=0.85",
                   fontsize=11)
    plt.tight_layout()
    fig_hmap = os.path.join(OUT_DIR, "fig_correlation_heatmap.png")
    plt.savefig(fig_hmap, dpi=150)
    plt.close()
    print(f"  Saved: {fig_hmap}")

    # Intra-cluster mean r
    unique_clusters = np.unique(cluster_ids)
    n_clusters = len(unique_clusters)
    high_r_clusters = []
    for cid in unique_clusters:
        members = cluster_series[cluster_series == cid].index.tolist()
        if len(members) < 2:
            continue
        sub = corr_sub.loc[members, members]
        upper_sub = sub.where(np.triu(np.ones(sub.shape), k=1).astype(bool)).stack().dropna()
        mean_r = upper_sub.mean()
        if mean_r > 0.85:
            high_r_clusters.append((cid, len(members), mean_r))
    print(f"  Total clusters: {n_clusters}")
    print(f"  Clusters with intra-cluster mean r > 0.85: {len(high_r_clusters)}")

# ══════════════════════════════════════════════════════════════════════════════
# Task 4 — Corridor cluster assignments
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 4] Saving corridor cluster assignments …")

if n_clust_stations < 2 or linkage_mat is None:
    # Degenerate case
    cluster_assign = pd.DataFrame({
        'station_id': valid_stations,
        'cluster_id': 1,
        'cluster_size': 1,
        'mean_intra_cluster_r': np.nan
    })
else:
    # Build full assignment table
    rows = []
    for cid in unique_clusters:
        members = cluster_series[cluster_series == cid].index.tolist()
        csize = len(members)
        if csize < 2:
            mir = np.nan
        else:
            sub = corr_sub.loc[members, members]
            up = sub.where(np.triu(np.ones(sub.shape), k=1).astype(bool)).stack().dropna()
            mir = up.mean()
        for sid in members:
            rows.append({
                'station_id': sid,
                'cluster_id': int(cid),
                'cluster_size': csize,
                'mean_intra_cluster_r': round(mir, 4) if not np.isnan(mir) else np.nan
            })
    cluster_assign = pd.DataFrame(rows)

    n_singletons = (cluster_assign['cluster_size'] == 1).sum()
    n_multi = (cluster_assign['cluster_size'] > 1).sum()
    print(f"  Singleton stations (cluster_size=1): {n_singletons}")
    print(f"  Multi-station clusters (total members): {n_multi}")
    print(f"  Multi-station clusters (unique): {(cluster_assign[cluster_assign['cluster_size']>1]['cluster_id'].nunique())}")

ca_out = os.path.join(OUT_DIR, "corridor_cluster_assignments.csv")
cluster_assign.to_csv(ca_out, index=False)
print(f"  Saved: {ca_out}")

# ══════════════════════════════════════════════════════════════════════════════
# Task 5 — Geographic distance and behavioral neighbors
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 5] Computing geographic distances and behavioral neighbors …")

def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance in km."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

# Only stations present in correlation matrix
geo = (
    master[master['station_id'].isin(corr_matrix.index)]
    [['station_id', 'latitude', 'longitude']]
    .dropna(subset=['latitude', 'longitude'])
    .set_index('station_id')
)
geo_stations = geo.index.tolist()
print(f"  Stations with coordinates: {len(geo_stations)}")

# Build geographic distance matrix
n_geo = len(geo_stations)
geo_dist = np.zeros((n_geo, n_geo))
lats = geo['latitude'].values
lons = geo['longitude'].values
for i in range(n_geo):
    geo_dist[i, :] = haversine_km(lats[i], lons[i], lats, lons)

geo_dist_df = pd.DataFrame(geo_dist, index=geo_stations, columns=geo_stations)

# Build behavioral neighbor table
beh_rows = []
corr_sub_geo = corr_matrix.reindex(index=geo_stations, columns=geo_stations)

for sid in geo_stations:
    # Geographic neighbors (k=5, excluding self)
    dist_row = geo_dist_df.loc[sid].drop(sid).sort_values()
    geo_neighbors = dist_row.head(K_NEIGHBORS).index.tolist()

    # Correlation row
    if sid in corr_sub_geo.index:
        corr_row = corr_sub_geo.loc[sid].drop(sid, errors='ignore').dropna().sort_values(ascending=False)
        top_corr = corr_row.head(K_NEIGHBORS).index.tolist()
    else:
        corr_row = pd.Series(dtype=float)
        top_corr = []

    # All candidate neighbors: union of geo and corr neighbors
    all_neighbors = list(set(geo_neighbors + top_corr))

    for nid in all_neighbors:
        if nid not in geo_stations:
            continue
        dist_km = geo_dist_df.loc[sid, nid]
        r_val = corr_sub_geo.loc[sid, nid] if (sid in corr_sub_geo.index and nid in corr_sub_geo.columns) else np.nan
        is_beh = (not np.isnan(r_val)) and (r_val > BEH_NEIGHBOR_R) and (dist_km <= BEH_NEIGHBOR_KM)
        beh_rows.append({
            'station_id': sid,
            'neighbor_station_id': nid,
            'pearson_r': round(r_val, 4) if not np.isnan(r_val) else np.nan,
            'distance_km': round(dist_km, 3),
            'is_behavioral_neighbor': is_beh
        })

beh_df = pd.DataFrame(beh_rows)
beh_out = os.path.join(OUT_DIR, "behavioral_neighbor_table.csv")
beh_df.to_csv(beh_out, index=False)
print(f"  Behavioral neighbor rows: {len(beh_df)}")
print(f"  Behavioral neighbor pairs (r>0.7 & dist<50km): {beh_df['is_behavioral_neighbor'].sum()}")
print(f"  Saved: {beh_out}")

# Count behavioral neighbors per station
n_beh = (
    beh_df[beh_df['is_behavioral_neighbor']]
    .groupby('station_id')['neighbor_station_id']
    .count()
    .rename('n_behavioral_neighbors')
)

# ══════════════════════════════════════════════════════════════════════════════
# Task 6 — Geographic cluster map
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 6] Plotting geographic cluster map …")

# Merge geo + cluster info
geo_plot = geo.copy()
geo_plot = geo_plot.merge(
    cluster_assign[['station_id', 'cluster_id', 'cluster_size']].set_index('station_id'),
    left_index=True, right_index=True, how='left'
)
geo_plot['cluster_id'] = geo_plot['cluster_id'].fillna(-1).astype(int)

# Assign colors
unique_cids = sorted(geo_plot['cluster_id'].unique())
palette = plt.cm.get_cmap('tab20', len(unique_cids))
cid_to_color = {cid: palette(i) for i, cid in enumerate(unique_cids)}

fig_map, ax_map = plt.subplots(figsize=(12, 9))
for cid in unique_cids:
    sub = geo_plot[geo_plot['cluster_id'] == cid]
    color = cid_to_color[cid]
    label = f"Cluster {cid}" if cid != -1 else "No cluster"
    ax_map.scatter(
        sub['longitude'], sub['latitude'],
        c=[color]*len(sub), s=60, alpha=0.8, edgecolors='k', linewidths=0.3,
        label=label, zorder=3
    )

# Cluster centroids
for cid in unique_cids:
    if cid == -1:
        continue
    sub = geo_plot[geo_plot['cluster_id'] == cid]
    if len(sub) < 2:
        continue
    cx = sub['longitude'].mean()
    cy = sub['latitude'].mean()
    ax_map.text(cx, cy, str(cid), fontsize=7, ha='center', va='center',
                fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.5))

ax_map.set_xlabel("Longitude", fontsize=11)
ax_map.set_ylabel("Latitude", fontsize=11)
ax_map.set_title(f"Geographic Distribution of Corridor Clusters\n"
                 f"{len(geo_plot)} stations, {len(unique_cids)} clusters "
                 f"(threshold r > 0.85)", fontsize=12)
# Legend only for clusters with ≥2 stations
handles, labels_leg = ax_map.get_legend_handles_labels()
# Show max 20 legend entries
if len(handles) > 20:
    handles, labels_leg = handles[:20], labels_leg[:20]
ax_map.legend(handles, labels_leg, fontsize=6, ncol=3, loc='lower right',
              framealpha=0.7, markerscale=0.8)
ax_map.grid(True, alpha=0.3, ls='--')
plt.tight_layout()
fig_map_out = os.path.join(OUT_DIR, "fig_geographic_clusters_map.png")
plt.savefig(fig_map_out, dpi=150)
plt.close()
print(f"  Saved: {fig_map_out}")

# ══════════════════════════════════════════════════════════════════════════════
# Task 7 — Reference station candidates
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Task 7] Identifying reference station candidates …")

# Merge everything needed
ref_base = master[['station_id', 'cosit', 'functional_class', 'fc_urban_rural',
                    'county', 'latitude', 'longitude', 'complete_months', 'n_sources']].copy()
ref_base = ref_base.merge(
    scorecard[['station_id', 'pct_complete']], on='station_id', how='left'
)
ref_base = ref_base.merge(
    cluster_assign[['station_id', 'cluster_id', 'cluster_size', 'mean_intra_cluster_r']],
    on='station_id', how='left'
)
ref_base = ref_base.merge(
    n_beh.reset_index(), on='station_id', how='left'
)
ref_base['n_behavioral_neighbors'] = ref_base['n_behavioral_neighbors'].fillna(0).astype(int)
ref_base['cluster_size'] = ref_base['cluster_size'].fillna(1).astype(int)

# Apply criteria
crit1 = ref_base['pct_complete'] >= 0.85
crit2 = ref_base['complete_months'] >= 10
crit3 = ref_base['n_behavioral_neighbors'] >= 2
crit4 = ref_base['n_sources'] == 3
crit5 = ref_base['cluster_size'] > 1

ref_candidates = ref_base[crit1 & crit2 & crit3 & crit4 & crit5].copy()

print(f"  Criterion 1 (pct_complete >= 0.85):  {crit1.sum()} stations pass")
print(f"  Criterion 2 (complete_months >= 10):  {crit2.sum()} stations pass")
print(f"  Criterion 3 (≥2 behavioral neighbors): {crit3.sum()} stations pass")
print(f"  Criterion 4 (n_sources == 3):         {crit4.sum()} stations pass")
print(f"  Criterion 5 (not singleton):           {crit5.sum()} stations pass")
print(f"  All 5 criteria:                        {len(ref_candidates)} stations")

# Rank
ref_candidates = ref_candidates.sort_values(
    ['pct_complete', 'n_behavioral_neighbors', 'complete_months'],
    ascending=[False, False, False]
).reset_index(drop=True)

ref_out_cols = [
    'station_id', 'functional_class', 'fc_urban_rural', 'county',
    'pct_complete', 'complete_months', 'cluster_id', 'n_behavioral_neighbors',
    'latitude', 'longitude'
]
ref_out = os.path.join(OUT_DIR, "reference_station_candidates.csv")
ref_candidates[ref_out_cols].to_csv(ref_out, index=False)
print(f"  Saved: {ref_out}")
if len(ref_candidates) > 0:
    print("\n  Top 10 reference candidates:")
    print(ref_candidates[ref_out_cols].head(10).to_string(index=False))

# ══════════════════════════════════════════════════════════════════════════════
# Report
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Report] Writing corridor_relationship_report.md …")

# Collect summary stats
n_clusters_total = cluster_assign['cluster_id'].nunique() if len(cluster_assign) else 0
n_singletons_final = (cluster_assign['cluster_size'] == 1).sum() if len(cluster_assign) else 0
n_multi_clusters = cluster_assign[cluster_assign['cluster_size'] > 1]['cluster_id'].nunique() if len(cluster_assign) else 0
beh_pairs_count = beh_df['is_behavioral_neighbor'].sum()
high_r_frac = (all_r > 0.85).mean() * 100 if len(all_r) else 0

report_text = f"""## Objective
Identify corridor relationships among GDOT ATR stations by computing pairwise
Pearson correlations of daily traffic volumes, applying hierarchical clustering
to group stations with similar temporal behavior, computing geographic and
behavioral proximity, and ranking reference station candidates for downstream
imputation and bias-correction work.

## Methods
- **Input stations**: {len(master_filt)} stations (in_5min_2024=True, n_sources≥2)
  from station_master_table.csv.
- **Daily volume matrix**: Built by reading raw 5-min data-1.csv files for the
  top {TOP_N_STATIONS} stations (ranked by pct_complete). For each station,
  5-min records with Coverage % ≥ 50 were summed to daily totals; only 2024
  dates were retained.
  - Matrix dimensions: {daily_matrix.shape[0]} dates × {daily_matrix.shape[1]} stations.
- **Correlation**: Pairwise Pearson r computed with min_periods={MIN_OVERLAP_DAYS}
  overlapping non-null days.
- **Clustering**: Scipy hierarchical linkage ('average' method) on distance = 1−r;
  flat clusters extracted at distance threshold {CLUSTER_DIST_THR} (equivalent to r > 0.85).
- **Behavioral neighbors**: A neighbor pair (within {BEH_NEIGHBOR_KM} km AND r > {BEH_NEIGHBOR_R}).
- **Reference candidates**: Must satisfy all 5 criteria (pct_complete ≥ 0.85,
  complete_months ≥ 10, ≥ 2 behavioral neighbors, n_sources = 3, not singleton).

## Key Findings
- **Valid station pairs** (≥{MIN_OVERLAP_DAYS} overlap days): {n_valid_pairs:,} pairs from
  {n_stations_corr} stations.
- **Pairwise r**: mean = {all_r.mean():.3f}, median = {all_r.median():.3f},
  range [{all_r.min():.3f}, {all_r.max():.3f}].
- **High-correlation pairs** (r > 0.85): {(all_r > 0.85).sum():,} pairs
  ({high_r_frac:.1f}% of all valid pairs).
- **Clusters found**: {n_clusters_total} total cluster IDs; {n_multi_clusters} multi-station
  corridor clusters; {n_singletons_final} singleton stations.
- **Behavioral neighbor pairs** (r > {BEH_NEIGHBOR_R}, dist < {BEH_NEIGHBOR_KM} km):
  {beh_pairs_count:,} pairs.
- **Reference station candidates**: {len(ref_candidates)} stations passed all 5 criteria.

## Tables/Plots Created
| File | Description |
|------|-------------|
| pairwise_correlation_matrix.csv | {n_stations_corr}×{n_stations_corr} Pearson r matrix |
| corridor_cluster_assignments.csv | Cluster IDs + intra-cluster stats for {len(cluster_assign)} stations |
| behavioral_neighbor_table.csv | {len(beh_df):,} station-neighbor rows with r and distance |
| reference_station_candidates.csv | {len(ref_candidates)} ranked reference candidates |
| fig_correlation_distribution.png | Histogram of pairwise r values |
| fig_correlation_heatmap.png | Clustered heatmap (reordered by cluster) |
| fig_geographic_clusters_map.png | Lat/lon scatter colored by cluster ID |

## Risks / Caveats
1. **Subset only**: Correlation matrix is built from the top {TOP_N_STATIONS} stations
   by data completeness; stations ranked 81+ are excluded and may form additional
   corridor groups not captured here.
2. **Min-overlap threshold**: Requiring ≥{MIN_OVERLAP_DAYS} overlapping non-null days
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
4. **Reference station validation**: For the {len(ref_candidates)} candidates, compare
   their hourly profiles (from station_hourly_profiles.csv) to verify they represent
   typical diurnal shapes for their functional class.
5. **Imputation design**: Use behavioral neighbors (r > {BEH_NEIGHBOR_R}, dist < {BEH_NEIGHBOR_KM} km)
   as donor stations for gap-filling; reference station candidates are the first-choice
   donors.
"""

report_out = os.path.join(OUT_DIR, "corridor_relationship_report.md")
with open(report_out, 'w') as f:
    f.write(report_text)
print(f"  Saved: {report_out}")

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("corridor_relationship_agent.py  COMPLETE  —", datetime.now())
print("Outputs written to:", OUT_DIR)
outputs = [
    "pairwise_correlation_matrix.csv",
    "corridor_cluster_assignments.csv",
    "behavioral_neighbor_table.csv",
    "reference_station_candidates.csv",
    "fig_correlation_distribution.png",
    "fig_correlation_heatmap.png",
    "fig_geographic_clusters_map.png",
    "corridor_relationship_report.md",
]
for f in outputs:
    fp = os.path.join(OUT_DIR, f)
    exists = "✓" if os.path.exists(fp) else "✗ MISSING"
    size = os.path.getsize(fp) if os.path.exists(fp) else 0
    print(f"  {exists}  {f}  ({size:,} bytes)")
print("=" * 70)
