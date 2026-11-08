"""
traffic_profile_agent.py
Phase 2A: Traffic Profile Characterization
Characterizes baseline traffic behavior across a stratified sample of GDOT stations.
"""

import os
import re
import warnings
import logging
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("/Users/kevinli/Desktop/Research_Gtech_gdot")
EDA_DIR    = BASE_DIR / "eda_output"
RAW_DIR    = BASE_DIR / "gdot_2025_data_total" / "CCS_5Min_2024"
OUT_DIR    = EDA_DIR / "profiles"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MASTER_CSV      = EDA_DIR / "inventory" / "station_master_table.csv"
SCORECARD_CSV   = EDA_DIR / "missingness" / "station_missingness_scorecard.csv"

N_SAMPLE   = 100
RANDOM_SEED = 42
COV_THRESH  = 50      # minimum Coverage % to keep a row

# ─────────────────────────────────────────────────────────────────────────────
# Task 1: Station sample selection
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 1: Station sample selection ===")

master = pd.read_csv(MASTER_CSV, dtype={"cosit": str})
scorecard = pd.read_csv(SCORECARD_CSV)

# Merge completeness info
merged = master.merge(scorecard[["station_id", "pct_complete"]], on="station_id", how="left")

# Filter: must be in 2024 data and sufficiently complete
eligible = merged[
    (merged["in_5min_2024"] == True) &
    (merged["pct_complete"].fillna(0) > 0.7)
].copy()

log.info(f"Eligible stations (in_5min_2024=True, pct_complete>0.7): {len(eligible)}")

# Build FC stratum label
eligible["stratum"] = eligible["functional_class"].astype(str) + "_" + eligible["fc_urban_rural"].astype(str)

# Enumerate actual data files in RAW_DIR
# Files named: GDOT_CCS-<12-digit COSIT>-data-1.csv
data_files = list(RAW_DIR.glob("GDOT_CCS-*-data-1.csv"))
log.info(f"Data-1 files found in RAW_DIR: {len(data_files)}")

# Extract cosit from filename (strip leading zeros for matching)
file_cosit_map = {}
for fp in data_files:
    m = re.search(r"GDOT_CCS-(\d+)-data-1\.csv", fp.name)
    if m:
        cosit_raw = m.group(1)           # zero-padded 12-digit string
        cosit_int = str(int(cosit_raw))  # strip leading zeros
        file_cosit_map[cosit_int] = fp

log.info(f"Unique COSITs with data-1.csv: {len(file_cosit_map)}")

# Map station cosit → file path
# cosit in master may have leading zeros or not; normalise to int-string
def norm_cosit(c):
    try:
        return str(int(str(c).strip()))
    except Exception:
        return None

eligible["cosit_norm"] = eligible["cosit"].apply(norm_cosit)
eligible["data_file"] = eligible["cosit_norm"].map(file_cosit_map)

# Keep only stations whose file actually exists
eligible = eligible[eligible["data_file"].notna()].copy()
log.info(f"Eligible stations with matching data file: {len(eligible)}")

# Stratified sample: proportional allocation, prefer high completeness
np.random.seed(RANDOM_SEED)
strata = eligible["stratum"].value_counts()
n_strata = len(strata)
total_eligible = len(eligible)
n_to_sample = min(N_SAMPLE, total_eligible)

# Proportional allocation
stratum_counts = (strata / total_eligible * n_to_sample).round().astype(int)
# Ensure at least 1 per stratum if possible, fix rounding
diff = n_to_sample - stratum_counts.sum()
if diff != 0:
    # Add/remove from largest strata
    idx_sorted = stratum_counts.sort_values(ascending=False).index
    for i in range(abs(int(diff))):
        stratum_counts[idx_sorted[i % len(idx_sorted)]] += int(np.sign(diff))

sampled_list = []
for stratum_name, n_s in stratum_counts.items():
    pool = eligible[eligible["stratum"] == stratum_name].sort_values("pct_complete", ascending=False)
    take = min(n_s, len(pool))
    if take > 0:
        sampled_list.append(pool.head(take))  # take top by completeness

sampled = pd.concat(sampled_list, ignore_index=True)
log.info(f"Final sample size: {len(sampled)} stations")
log.info(f"Stratum distribution:\n{sampled['stratum'].value_counts().to_string()}")


# ─────────────────────────────────────────────────────────────────────────────
# Task 2 & 3: Load data, compute per-station profiles
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Tasks 2 & 3: Load data and compute per-station profiles ===")

F_COLS = [f"F{i}" for i in range(1, 16)]

# Storage
daily_records   = []
hourly_records  = []
dow_records     = []
monthly_records = []
summary_records = []
skipped_stations = []

def safe_to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

for idx, row in sampled.iterrows():
    sid = row["station_id"]
    fp  = row["data_file"]

    try:
        df = pd.read_csv(fp, low_memory=False)
    except Exception as e:
        log.warning(f"SKIP {sid}: cannot read {fp}: {e}")
        skipped_stations.append(sid)
        continue

    # Validate required columns
    if "Start Time" not in df.columns or "Count" not in df.columns:
        log.warning(f"SKIP {sid}: missing required columns")
        skipped_stations.append(sid)
        continue

    # Parse datetime
    df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
    df = df.dropna(subset=["Start Time"])

    # Coverage filter
    if "Coverage %" in df.columns:
        df["Coverage %"] = safe_to_numeric(df["Coverage %"])
        df = df[df["Coverage %"] >= COV_THRESH]

    if len(df) == 0:
        log.warning(f"SKIP {sid}: no rows after coverage filter")
        skipped_stations.append(sid)
        continue

    df["Count"] = safe_to_numeric(df["Count"])

    # Numeric F columns
    available_fcols = [c for c in F_COLS if c in df.columns]
    for c in available_fcols:
        df[c] = safe_to_numeric(df[c])

    # Time features
    df["date"]          = df["Start Time"].dt.date
    df["hour"]          = df["Start Time"].dt.hour
    df["dow"]           = df["Start Time"].dt.dayofweek   # 0=Mon
    df["month"]         = df["Start Time"].dt.month
    df["is_weekday"]    = df["dow"] < 5

    # Sum across directions per timestamp
    grp_cols = ["date", "hour", "dow", "month", "is_weekday", "Start Time"]
    agg_dict = {"Count": "sum"}
    for c in available_fcols:
        agg_dict[c] = "sum"

    # Group by timestamp (handles multiple direction rows)
    ts_agg = df.groupby("Start Time").agg(agg_dict).reset_index()
    ts_agg["date"]       = ts_agg["Start Time"].dt.date
    ts_agg["hour"]       = ts_agg["Start Time"].dt.hour
    ts_agg["dow"]        = ts_agg["Start Time"].dt.dayofweek
    ts_agg["month"]      = ts_agg["Start Time"].dt.month
    ts_agg["is_weekday"] = ts_agg["dow"] < 5

    # ── Daily volume ──
    daily = ts_agg.groupby("date").agg(
        daily_count=("Count", "sum"),
        dow=("dow", "first"),
        month=("month", "first"),
        is_weekday=("is_weekday", "first")
    ).reset_index()

    if len(daily) == 0:
        log.warning(f"SKIP {sid}: no daily data")
        skipped_stations.append(sid)
        continue

    weekday_daily = daily[daily["is_weekday"]]["daily_count"]
    weekend_daily = daily[~daily["is_weekday"]]["daily_count"]

    med_daily      = daily["daily_count"].median()
    mean_daily     = daily["daily_count"].mean()
    p10_daily      = daily["daily_count"].quantile(0.10)
    p90_daily      = daily["daily_count"].quantile(0.90)
    weekday_med    = weekday_daily.median() if len(weekday_daily) > 0 else np.nan
    weekend_med    = weekend_daily.median() if len(weekend_daily) > 0 else np.nan
    wk_wknd_ratio  = (weekday_med / weekend_med) if (weekend_med and weekend_med > 0) else np.nan

    summary_records.append({
        "station_id": sid,
        "functional_class": row["functional_class"],
        "fc_urban_rural": row["fc_urban_rural"],
        "pct_complete": row["pct_complete"],
        "n_days": len(daily),
        "median_daily_volume": med_daily,
        "mean_daily_volume": mean_daily,
        "p10_daily": p10_daily,
        "p90_daily": p90_daily,
        "weekday_median": weekday_med,
        "weekend_median": weekend_med,
        "weekday_weekend_ratio": wk_wknd_ratio,
    })

    # ── Hourly profile ──
    for is_wd, label in [(True, "weekday"), (False, "weekend")]:
        subset = ts_agg[ts_agg["is_weekday"] == is_wd]
        if len(subset) == 0:
            continue
        hourly_mean = subset.groupby("hour")["Count"].mean().reset_index()
        hourly_mean.columns = ["hour", "mean_count"]
        hourly_mean["station_id"] = sid
        hourly_mean["day_type"] = label
        hourly_mean["functional_class"] = row["functional_class"]
        hourly_records.append(hourly_mean)

    # ── AM/PM peak hours (weekday only) ──
    wd_hourly = ts_agg[ts_agg["is_weekday"]].groupby("hour")["Count"].mean()
    am_range = wd_hourly.loc[wd_hourly.index.isin(range(6, 12))]
    pm_range = wd_hourly.loc[wd_hourly.index.isin(range(15, 21))]
    am_peak = int(am_range.idxmax()) if len(am_range) > 0 else np.nan
    pm_peak = int(pm_range.idxmax()) if len(pm_range) > 0 else np.nan

    summary_records[-1]["am_peak_hour"] = am_peak
    summary_records[-1]["pm_peak_hour"] = pm_peak

    # ── DOW profile ──
    dow_profile = ts_agg.groupby(["date", "dow"]).agg(daily_count=("Count", "sum")).reset_index()
    dow_mean = dow_profile.groupby("dow")["daily_count"].mean().reset_index()
    dow_mean.columns = ["dow", "mean_daily_volume"]
    dow_mean["station_id"] = sid
    dow_mean["functional_class"] = row["functional_class"]
    dow_records.append(dow_mean)

    # ── Monthly profile ──
    monthly_profile = ts_agg.groupby(["date", "month"]).agg(daily_count=("Count", "sum")).reset_index()
    monthly_mean = monthly_profile.groupby("month")["daily_count"].mean().reset_index()
    monthly_mean.columns = ["month", "mean_daily_volume"]
    monthly_mean["station_id"] = sid
    monthly_mean["functional_class"] = row["functional_class"]
    monthly_records.append(monthly_mean)

    # ── Vehicle mix ──
    if available_fcols:
        total_classified = ts_agg[available_fcols].sum(axis=1)
        total_classified_sum = total_classified.sum()
        if total_classified_sum > 0:
            f_fracs = {}
            for c in available_fcols:
                f_fracs[f"{c}_frac"] = ts_agg[c].sum() / total_classified_sum
            pct_heavy = sum(ts_agg[c].sum() for c in available_fcols if int(c[1:]) >= 4) / total_classified_sum
        else:
            f_fracs = {f"{c}_frac": np.nan for c in available_fcols}
            pct_heavy = np.nan
        summary_records[-1].update(f_fracs)
        summary_records[-1]["pct_heavy"] = pct_heavy
    else:
        summary_records[-1]["pct_heavy"] = np.nan

    # Store for daily records
    for _, drow in daily.iterrows():
        daily_records.append({
            "station_id": sid,
            "date": drow["date"],
            "daily_count": drow["daily_count"],
            "dow": drow["dow"],
            "month": drow["month"],
            "is_weekday": drow["is_weekday"],
            "functional_class": row["functional_class"],
        })

log.info(f"Successfully processed: {len(summary_records)} stations, skipped: {len(skipped_stations)}")
if skipped_stations:
    log.info(f"Skipped station IDs: {skipped_stations}")

# ── Compile DataFrames ──
df_summary  = pd.DataFrame(summary_records)
df_hourly   = pd.concat(hourly_records, ignore_index=True) if hourly_records else pd.DataFrame()
df_dow      = pd.concat(dow_records,    ignore_index=True) if dow_records    else pd.DataFrame()
df_monthly  = pd.concat(monthly_records, ignore_index=True) if monthly_records else pd.DataFrame()
df_daily_all = pd.DataFrame(daily_records)

# Save CSVs
df_summary.to_csv(OUT_DIR / "station_daily_volume_summary.csv", index=False)
df_hourly.to_csv(OUT_DIR / "station_hourly_profiles.csv", index=False)
df_dow.to_csv(OUT_DIR / "station_dow_profiles.csv", index=False)
df_monthly.to_csv(OUT_DIR / "station_monthly_profiles.csv", index=False)
log.info("Saved per-station profile CSVs")

n_stations = len(df_summary)

# ─────────────────────────────────────────────────────────────────────────────
# Task 4: Aggregate profiles by functional class
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 4: Aggregate profiles by functional class ===")

# ── Fig 1: Hourly profile by FC (normalized 0-1) ──
if not df_hourly.empty:
    wd_hourly = df_hourly[df_hourly["day_type"] == "weekday"]
    fc_hourly = wd_hourly.groupby(["functional_class", "hour"])["mean_count"].median().reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))
    fc_list = sorted(fc_hourly["functional_class"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(fc_list)))

    for fc, color in zip(fc_list, colors):
        sub = fc_hourly[fc_hourly["functional_class"] == fc].sort_values("hour")
        vals = sub["mean_count"].values
        rng = vals.max() - vals.min()
        norm_vals = (vals - vals.min()) / rng if rng > 0 else vals * 0
        ax.plot(sub["hour"], norm_vals, label=fc, color=color, linewidth=2, marker="o", markersize=3)

    ax.set_xlabel("Hour of Day", fontsize=12)
    ax.set_ylabel("Normalized Mean Count (0–1)", fontsize=12)
    ax.set_title(f"Weekday Hourly Traffic Profile by Functional Class (n={n_stations} stations)", fontsize=13)
    ax.set_xticks(range(0, 24))
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, title="Functional Class")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_hourly_profile_by_fc.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_hourly_profile_by_fc.png")

# ── Fig 2: DOW profile by FC ──
if not df_dow.empty:
    fc_dow = df_dow.groupby(["functional_class", "dow"])["mean_daily_volume"].median().reset_index()
    fc_list = sorted(fc_dow["functional_class"].unique())
    n_fc = len(fc_list)
    dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(7)
    width = 0.8 / n_fc
    colors = plt.cm.tab10(np.linspace(0, 1, n_fc))

    for i, (fc, color) in enumerate(zip(fc_list, colors)):
        sub = fc_dow[fc_dow["functional_class"] == fc].set_index("dow").reindex(range(7))["mean_daily_volume"]
        ax.bar(x + i * width - (n_fc - 1) * width / 2, sub.values, width=width, label=fc, color=color, alpha=0.85)

    ax.set_xlabel("Day of Week", fontsize=12)
    ax.set_ylabel("Median Daily Volume (counts)", fontsize=12)
    ax.set_title(f"Day-of-Week Traffic Profile by Functional Class (n={n_stations} stations)", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(dow_labels)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, title="Functional Class")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_dow_profile_by_fc.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_dow_profile_by_fc.png")

# ── Fig 3: Monthly profile (averaged across all stations) ──
if not df_monthly.empty:
    monthly_agg = df_monthly.groupby("month")["mean_daily_volume"].median().reset_index()
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(monthly_agg["month"], monthly_agg["mean_daily_volume"], color="steelblue", alpha=0.85, edgecolor="white")
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Median Daily Volume (counts)", fontsize=12)
    ax.set_title(f"Monthly Traffic Profile – All Stations (n={n_stations})", fontsize=13)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels, rotation=45)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_monthly_profile.png", dpi=150)
    plt.close()
    log.info("Saved fig_monthly_profile.png")


# ─────────────────────────────────────────────────────────────────────────────
# Task 5: Weekday vs Weekend ratio
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 5: Weekday/weekend ratio ===")

if not df_summary.empty and "weekday_weekend_ratio" in df_summary.columns:
    ratio_data = df_summary[df_summary["weekday_weekend_ratio"].notna()]
    fc_list = sorted(ratio_data["functional_class"].unique())
    colors_map = {fc: plt.cm.tab10(i / max(len(fc_list) - 1, 1)) for i, fc in enumerate(fc_list)}

    fig, ax = plt.subplots(figsize=(10, 5))
    for fc in fc_list:
        sub = ratio_data[ratio_data["functional_class"] == fc]["weekday_weekend_ratio"]
        ax.hist(sub, bins=20, alpha=0.55, label=fc, color=colors_map[fc], edgecolor="none")

    ax.axvline(x=1.0, color="black", linestyle="--", linewidth=1, label="Ratio=1 (equal)")
    ax.set_xlabel("Weekday / Weekend Volume Ratio", fontsize=12)
    ax.set_ylabel("Number of Stations", fontsize=12)
    ax.set_title(f"Weekday/Weekend Volume Ratio Distribution (n={n_stations} stations)", fontsize=13)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, title="Functional Class")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_weekday_weekend_ratio.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_weekday_weekend_ratio.png")


# ─────────────────────────────────────────────────────────────────────────────
# Task 6: Vehicle mix analysis
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 6: Vehicle mix analysis ===")

frac_cols = [f"F{i}_frac" for i in range(1, 16)]
avail_frac = [c for c in frac_cols if c in df_summary.columns]

if avail_frac:
    mix_data = df_summary[["functional_class"] + avail_frac].dropna(subset=avail_frac, how="all")
    fc_mix = mix_data.groupby("functional_class")[avail_frac].median()

    # Normalize each row to sum to 1
    row_sums = fc_mix.sum(axis=1)
    fc_mix_norm = fc_mix.div(row_sums, axis=0).fillna(0)

    fc_labels = fc_mix_norm.index.tolist()
    f_labels = [f"F{i}" for i in range(1, 16)]
    cmap = plt.cm.tab20(np.linspace(0, 1, len(avail_frac)))

    fig, ax = plt.subplots(figsize=(12, 6))
    bottoms = np.zeros(len(fc_labels))
    for j, (fc_col, label, color) in enumerate(zip(avail_frac, f_labels, cmap)):
        vals = fc_mix_norm[fc_col].values if fc_col in fc_mix_norm.columns else np.zeros(len(fc_labels))
        ax.bar(fc_labels, vals, bottom=bottoms, label=label, color=color, edgecolor="white", linewidth=0.3)
        bottoms += vals

    ax.set_xlabel("Functional Class", fontsize=11)
    ax.set_ylabel("Fraction of Classified Volume", fontsize=11)
    ax.set_title(f"Vehicle Class Mix by Functional Class (n={n_stations} stations)", fontsize=13)
    ax.set_xticklabels(fc_labels, rotation=45, ha="right", fontsize=8)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, ncol=1, title="F-Class")
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_vehicle_mix_by_fc.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_vehicle_mix_by_fc.png")


# ─────────────────────────────────────────────────────────────────────────────
# Task 7: AM/PM peak hour distribution
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 7: AM/PM peak hour distribution ===")

if "am_peak_hour" in df_summary.columns and "pm_peak_hour" in df_summary.columns:
    am_data = df_summary["am_peak_hour"].dropna().astype(int)
    pm_data = df_summary["pm_peak_hour"].dropna().astype(int)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.hist(am_data, bins=range(6, 13), align="left", color="steelblue", edgecolor="white", rwidth=0.8)
    ax1.set_xlabel("AM Peak Hour (6–11)", fontsize=12)
    ax1.set_ylabel("Number of Stations", fontsize=12)
    ax1.set_title(f"AM Peak Hour Distribution (n={len(am_data)} stations)", fontsize=12)
    ax1.set_xticks(range(6, 12))
    ax1.set_xticklabels([f"{h}:00" for h in range(6, 12)])
    ax1.grid(True, alpha=0.3)

    ax2.hist(pm_data, bins=range(15, 22), align="left", color="tomato", edgecolor="white", rwidth=0.8)
    ax2.set_xlabel("PM Peak Hour (15–20)", fontsize=12)
    ax2.set_ylabel("Number of Stations", fontsize=12)
    ax2.set_title(f"PM Peak Hour Distribution (n={len(pm_data)} stations)", fontsize=12)
    ax2.set_xticks(range(15, 21))
    ax2.set_xticklabels([f"{h}:00" for h in range(15, 21)])
    ax2.grid(True, alpha=0.3)

    plt.suptitle("Weekday AM and PM Peak Hour Distribution Across Stations", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_am_pm_peak_hour_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_am_pm_peak_hour_distribution.png")


# ─────────────────────────────────────────────────────────────────────────────
# Task 8: Station archetypes via k-means
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 8: Station archetypes ===")

# Normalize median daily volume
df_summary["median_daily_volume_norm"] = (
    (df_summary["median_daily_volume"] - df_summary["median_daily_volume"].min()) /
    (df_summary["median_daily_volume"].max() - df_summary["median_daily_volume"].min() + 1e-9)
)

feature_cols = ["weekday_weekend_ratio", "am_peak_hour", "pm_peak_hour", "pct_heavy", "median_daily_volume_norm"]
avail_feat = [c for c in feature_cols if c in df_summary.columns]

archetype_df = df_summary[["station_id", "functional_class", "fc_urban_rural"] + avail_feat].copy()
archetype_df = archetype_df.dropna(subset=avail_feat, how="any")

log.info(f"Stations with complete archetype features: {len(archetype_df)}")

if len(archetype_df) >= 4:
    X = archetype_df[avail_feat].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=4, random_state=RANDOM_SEED, n_init=20, max_iter=500)
    archetype_df["cluster"] = kmeans.fit_predict(X_scaled)

    # Characterize clusters to assign labels
    cluster_stats = archetype_df.groupby("cluster")[avail_feat].mean()
    log.info(f"Cluster centers:\n{cluster_stats.to_string()}")

    # Assign labels based on cluster characteristics
    # Commuter: high weekday/weekend ratio, clear AM+PM peaks
    # Freight/Arterial: high pct_heavy
    # Rural: low median_daily_volume_norm
    # Mixed: moderate everything
    def assign_label(row):
        c = int(row["cluster"])
        stats = cluster_stats.loc[c]
        pct_h = stats.get("pct_heavy", 0) if not np.isnan(stats.get("pct_heavy", np.nan)) else 0
        wkratio = stats.get("weekday_weekend_ratio", 1) if not np.isnan(stats.get("weekday_weekend_ratio", np.nan)) else 1
        vol_norm = stats.get("median_daily_volume_norm", 0.5) if not np.isnan(stats.get("median_daily_volume_norm", np.nan)) else 0.5

        if pct_h == cluster_stats["pct_heavy"].max():
            return "Freight/Arterial"
        elif vol_norm == cluster_stats["median_daily_volume_norm"].min():
            return "Rural"
        elif wkratio == cluster_stats["weekday_weekend_ratio"].max():
            return "Commuter"
        else:
            return "Mixed"

    archetype_df["archetype"] = archetype_df.apply(assign_label, axis=1)
    log.info(f"Archetype distribution:\n{archetype_df['archetype'].value_counts().to_string()}")

    # Save archetypes
    archetype_df.to_csv(OUT_DIR / "station_archetypes.csv", index=False)
    log.info("Saved station_archetypes.csv")
else:
    log.warning("Not enough stations for clustering; creating empty archetype file")
    archetype_df["cluster"] = np.nan
    archetype_df["archetype"] = "Unknown"
    archetype_df.to_csv(OUT_DIR / "station_archetypes.csv", index=False)


# ─────────────────────────────────────────────────────────────────────────────
# Task 9: Archetype summary plot
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Task 9: Archetype summary plot ===")

if not df_hourly.empty and "archetype" in archetype_df.columns:
    archetype_map = archetype_df.set_index("station_id")["archetype"].to_dict()
    df_hourly["archetype"] = df_hourly["station_id"].map(archetype_map)
    hourly_wd_archetype = df_hourly[(df_hourly["day_type"] == "weekday") & df_hourly["archetype"].notna()]

    archetypes_found = hourly_wd_archetype["archetype"].unique()
    archetype_order = ["Commuter", "Freight/Arterial", "Rural", "Mixed"]
    archetypes_plot = [a for a in archetype_order if a in archetypes_found]
    # Add any archetypes not in our predefined order
    for a in archetypes_found:
        if a not in archetypes_plot:
            archetypes_plot.append(a)

    n_arc = len(archetypes_plot)
    rows = 2
    cols = 2
    fig, axes = plt.subplots(rows, cols, figsize=(14, 9), sharey=False)
    axes_flat = axes.flatten()

    arch_colors = {"Commuter": "steelblue", "Freight/Arterial": "tomato",
                   "Rural": "forestgreen", "Mixed": "darkorange"}

    for i, arch in enumerate(archetypes_plot[:4]):
        ax = axes_flat[i]
        sub = hourly_wd_archetype[hourly_wd_archetype["archetype"] == arch]
        n_st = sub["station_id"].nunique()
        profile = sub.groupby("hour")["mean_count"].median().reindex(range(24), fill_value=np.nan)
        color = arch_colors.get(arch, f"C{i}")
        ax.plot(profile.index, profile.values, color=color, linewidth=2.5, marker="o", markersize=4)
        ax.fill_between(profile.index, profile.values, alpha=0.15, color=color)
        ax.set_title(f"{arch} (n={n_st} stations)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Hour of Day", fontsize=10)
        ax.set_ylabel("Median Count per 5-min Bin", fontsize=10)
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3)

    # Hide unused subplots
    for j in range(n_arc, 4):
        axes_flat[j].set_visible(False)

    plt.suptitle(f"Average Weekday Hourly Profile by Station Archetype (n={n_stations} stations)", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig_archetype_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved fig_archetype_summary.png")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics for the report
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Collecting summary statistics for report ===")

med_vol   = df_summary["median_daily_volume"].median() if "median_daily_volume" in df_summary else np.nan
mean_vol  = df_summary["mean_daily_volume"].mean() if "mean_daily_volume" in df_summary else np.nan
med_wkratio = df_summary["weekday_weekend_ratio"].median() if "weekday_weekend_ratio" in df_summary else np.nan
am_mode   = df_summary["am_peak_hour"].mode().iloc[0] if "am_peak_hour" in df_summary and len(df_summary["am_peak_hour"].dropna()) > 0 else "N/A"
pm_mode   = df_summary["pm_peak_hour"].mode().iloc[0] if "pm_peak_hour" in df_summary and len(df_summary["pm_peak_hour"].dropna()) > 0 else "N/A"

fc_summary = df_summary.groupby("functional_class").agg(
    n_stations=("station_id", "count"),
    median_daily_volume=("median_daily_volume", "median"),
    weekday_weekend_ratio=("weekday_weekend_ratio", "median"),
).reset_index()

archetype_counts = archetype_df["archetype"].value_counts().to_dict() if "archetype" in archetype_df.columns else {}

# ─────────────────────────────────────────────────────────────────────────────
# Write traffic_profile_report.md
# ─────────────────────────────────────────────────────────────────────────────
log.info("=== Writing traffic_profile_report.md ===")

report_lines = [
    "## Objective",
    "",
    "Characterize baseline 2024 traffic behavior (volume, temporal patterns, vehicle mix, and station archetypes) "
    "across a stratified sample of GDOT 5-minute count stations. This is Phase 2A of the GDOT EDA workflow.",
    "",
    "## Methods",
    "",
    f"- **Input data**: 2024 CCS 5-minute count CSVs from {RAW_DIR.name}; station master table and missingness scorecard from prior phases.",
    f"- **Eligibility filter**: `in_5min_2024 == True` AND `pct_complete > 0.7` → {len(eligible)} eligible stations.",
    f"- **Stratified sample**: {n_stations} stations sampled proportionally across functional-class × urban/rural strata, "
    "preferring stations with highest completeness.",
    f"- **Coverage filter**: Only 5-min bins with Coverage % ≥ {COV_THRESH}% were used to avoid treating outages as zeros.",
    "- **Direction aggregation**: Multiple direction rows per timestamp were summed to get station-level totals.",
    "- **Profiles computed**: Daily volume summary, hourly (weekday/weekend), day-of-week, and monthly.",
    "- **Vehicle mix**: F1–F15 bins normalized to fraction of total classified volume.",
    "- **Archetypes**: k-means (k=4) clustering on weekday/weekend ratio, AM/PM peak hour, pct-heavy-vehicle, "
    "and normalized median daily volume; clusters labeled by dominant characteristic.",
    "",
    "## Key Findings",
    "",
    f"- **Stations processed**: {n_stations} (skipped {len(skipped_stations)} due to missing/corrupt files).",
    f"- **Median daily volume** across all sampled stations: {med_vol:,.0f} counts/day." if not np.isnan(med_vol) else "- Median daily volume: N/A.",
    f"- **Mean daily volume** across all sampled stations: {mean_vol:,.0f} counts/day." if not np.isnan(mean_vol) else "- Mean daily volume: N/A.",
    f"- **Weekday/weekend ratio**: median = {med_wkratio:.2f} — indicating most stations carry {'more' if med_wkratio > 1 else 'less'} traffic on weekdays." if not np.isnan(med_wkratio) else "- Weekday/weekend ratio: N/A.",
    f"- **AM peak hour** (most common across stations): {am_peak_hour if isinstance(am_mode, str) else int(am_mode)}:00.",
    f"- **PM peak hour** (most common): {int(pm_mode)}:00." if not isinstance(pm_mode, str) else f"- **PM peak hour**: {pm_mode}.",
    "",
    "### Volume by Functional Class",
    "",
    fc_summary.to_markdown(index=False) if hasattr(fc_summary, "to_markdown") else fc_summary.to_string(),
    "",
    "### Archetype Distribution",
    "",
]

for arch, cnt in archetype_counts.items():
    report_lines.append(f"- **{arch}**: {cnt} stations")

report_lines += [
    "",
    "## Tables/Plots Created",
    "",
    "| File | Description |",
    "|------|-------------|",
    "| `station_daily_volume_summary.csv` | Per-station daily volume statistics and peak hours |",
    "| `station_hourly_profiles.csv` | Per-station hourly mean counts (weekday/weekend) |",
    "| `station_dow_profiles.csv` | Per-station day-of-week mean daily volumes |",
    "| `station_monthly_profiles.csv` | Per-station monthly mean daily volumes |",
    "| `station_archetypes.csv` | Station archetype labels and clustering features |",
    "| `fig_hourly_profile_by_fc.png` | Normalized weekday hourly profiles by functional class |",
    "| `fig_dow_profile_by_fc.png` | Day-of-week profiles by functional class |",
    "| `fig_monthly_profile.png` | Monthly mean daily volume across all stations |",
    "| `fig_weekday_weekend_ratio.png` | Distribution of weekday/weekend ratio by FC |",
    "| `fig_vehicle_mix_by_fc.png` | F1–F15 vehicle mix stacked bar by FC |",
    "| `fig_am_pm_peak_hour_distribution.png` | Histograms of AM and PM peak hours |",
    "| `fig_archetype_summary.png` | 2×2 average weekday hourly profiles by archetype |",
    "",
    "## Risks/Caveats",
    "",
    "- Analysis uses only `data-1.csv` per station; additional data files (`data-2.csv`, `data-3.csv`) are excluded.",
    "- Coverage % filter (≥50%) may still include periods with partial lane failures.",
    "- F1–F15 fractions are only meaningful when classified volume > 0; stations with poor classifier coverage may show skewed mixes.",
    "- k-means archetype labels are heuristic; boundary cases may be mis-assigned.",
    "- Stratified sampling favors completeness; less reliable stations are underrepresented.",
    f"- {len(skipped_stations)} stations were skipped due to file read errors or empty data after filtering.",
    "",
    "## Recommended Next Steps",
    "",
    "- **Phase 2B (speed profile agent)**: Analyze speed bin distributions alongside volume.",
    "- **Outlier investigation**: Examine stations with extreme weekday/weekend ratios (>3 or <0.5).",
    "- **Seasonal decomposition**: Fit STL or similar models to monthly profiles to separate trend from seasonality.",
    "- **Archetype validation**: Cross-reference archetypes with land-use/AADT data for external validation.",
    "- **Lane-level analysis**: Incorporate direction-split data for directional peak analysis.",
    "- **Missing data imputation**: Use archetype profiles to impute gaps in incomplete stations.",
]

report_text = "\n".join(report_lines)
with open(OUT_DIR / "traffic_profile_report.md", "w") as f:
    f.write(report_text)
log.info("Saved traffic_profile_report.md")

# ─────────────────────────────────────────────────────────────────────────────
# Final file verification
# ─────────────────────────────────────────────────────────────────────────────
required_files = [
    "station_daily_volume_summary.csv",
    "station_hourly_profiles.csv",
    "station_dow_profiles.csv",
    "station_monthly_profiles.csv",
    "station_archetypes.csv",
    "fig_hourly_profile_by_fc.png",
    "fig_dow_profile_by_fc.png",
    "fig_monthly_profile.png",
    "fig_weekday_weekend_ratio.png",
    "fig_vehicle_mix_by_fc.png",
    "fig_am_pm_peak_hour_distribution.png",
    "fig_archetype_summary.png",
    "traffic_profile_report.md",
]

log.info("=== Output file verification ===")
all_ok = True
for fname in required_files:
    fpath = OUT_DIR / fname
    if fpath.exists():
        size_kb = fpath.stat().st_size / 1024
        log.info(f"  OK  {fname} ({size_kb:.1f} KB)")
    else:
        log.error(f"  MISSING: {fname}")
        all_ok = False

if all_ok:
    log.info("All required output files present. Phase 2A complete.")
else:
    log.error("Some output files are missing — check logs above.")

print("\n=== DONE ===")
print(f"Stations sampled: {n_stations}")
print(f"Stations skipped: {len(skipped_stations)}")
print(f"Output directory: {OUT_DIR}")
