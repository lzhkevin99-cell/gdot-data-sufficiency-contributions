"""
missingness_quality_agent.py
Phase 1B: Deep Missingness Audit of GDOT Traffic Dataset
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from pathlib import Path
from itertools import groupby

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
OUT_DIR = Path("/Users/kevinli/Desktop/Research_Gtech_gdot/eda_output/missingness")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DATA_ROOT = Path("/Users/kevinli/Desktop/Research_Gtech_gdot/gdot_2025_data_total")
OUTPUT_ROOT = Path("/Users/kevinli/Desktop/Research_Gtech_gdot/outputs")
STATION_MASTER = Path("/Users/kevinli/Desktop/Research_Gtech_gdot/eda_output/inventory/station_master_table.csv")
CCS_2024_DIR = DATA_ROOT / "CCS_5Min_2024"

# ── Helper: classify coverage_pct ─────────────────────────────────────────────
def classify_coverage(pct):
    if pd.isna(pct):
        return "ABSENT"
    elif pct >= 80:
        return "COMPLETE"
    elif pct >= 60:
        return "PARTIAL_MINOR"
    elif pct >= 40:
        return "PARTIAL_MAJOR"
    elif pct > 0:
        return "SPARSE"
    else:
        return "ABSENT"

# ── Task 1: Load completeness CSVs ────────────────────────────────────────────
print("=" * 70)
print("TASK 1: Loading completeness CSVs")
print("=" * 70)

# --- 2024 ---
df24 = pd.read_csv(OUTPUT_ROOT / "completeness_2024.csv")
# cosit column — map to station_id via station_master later, but also carry cosit
# Schema: cosit, year, month, observed_bins, expected_bins, n_directions, completeness_pct, complete, station_name
print(f"  2024: {len(df24)} rows, cols: {list(df24.columns)}")
# Use station_name as station_id for 2024 (matches other sources)
df24 = df24.rename(columns={"station_name": "station_id"})
df24["source"] = "2024"

# --- 2022-2023 ---
df23 = pd.read_csv(OUTPUT_ROOT / "completeness_2022_2023.csv")
# Schema: station_name, year, month, observed_bins, n_lanes, expected_bins, completeness_pct, complete
print(f"  2022-2023: {len(df23)} rows, cols: {list(df23.columns)}")
df23 = df23.rename(columns={"station_name": "station_id"})
df23["source"] = "2022_2023"

# --- 2017-2022 ---
df17 = pd.read_csv(OUTPUT_ROOT / "completeness_2017_2022.csv")
# Schema: station_name, year, month, observed_bins, n_directions, expected_bins, completeness_pct, complete
print(f"  2017-2022: {len(df17)} rows, cols: {list(df17.columns)}")
df17 = df17.rename(columns={"station_name": "station_id"})
df17["source"] = "2017_2022"

# Unify columns
keep_cols = ["station_id", "year", "month", "completeness_pct"]
df_all = pd.concat([
    df24[keep_cols],
    df23[keep_cols],
    df17[keep_cols],
], ignore_index=True)

# Deduplicate: if same station/year/month appears in multiple sources keep max coverage
df_all = (df_all
          .sort_values("completeness_pct", ascending=False)
          .drop_duplicates(subset=["station_id", "year", "month"])
          .reset_index(drop=True))

print(f"  Combined unique station-months: {len(df_all)}")
print(f"  Unique stations: {df_all['station_id'].nunique()}")
print(f"  Year range: {df_all['year'].min()} – {df_all['year'].max()}")

# Apply quality flag
df_all["quality_flag"] = df_all["completeness_pct"].apply(classify_coverage)

# ── Station-month issue table ─────────────────────────────────────────────────
smit = df_all[["station_id", "year", "month", "completeness_pct", "quality_flag"]].copy()
smit["coverage_pct"] = smit["completeness_pct"]
smit = smit.drop(columns=["completeness_pct"])
smit.to_csv(OUT_DIR / "station_month_issue_table.csv", index=False)
print(f"  Saved station_month_issue_table.csv ({len(smit)} rows)")

# ── Build full station-month grid to capture ABSENT months ───────────────────
all_stations = df_all["station_id"].unique()
all_years = range(2017, 2025)
all_months = range(1, 13)
grid = pd.MultiIndex.from_product([all_stations, all_years, all_months],
                                   names=["station_id", "year", "month"])
grid_df = pd.DataFrame(index=grid).reset_index()

# Only keep station-year combos that are within the station's observed range
# Load master for date range info
master = pd.read_csv(STATION_MASTER)
master["first_year"] = pd.to_datetime(master["first_date"]).dt.year
master["first_month"] = pd.to_datetime(master["first_date"]).dt.month
master["last_year"] = pd.to_datetime(master["last_date"]).dt.year
master["last_month"] = pd.to_datetime(master["last_date"]).dt.month

# Merge grid with master to filter valid station-months
grid_df = grid_df.merge(master[["station_id", "first_year", "first_month",
                                  "last_year", "last_month"]], on="station_id", how="left")
# Filter to within station's date range
grid_df["ym_int"] = grid_df["year"] * 100 + grid_df["month"]
grid_df["first_ym"] = grid_df["first_year"] * 100 + grid_df["first_month"]
grid_df["last_ym"] = grid_df["last_year"] * 100 + grid_df["last_month"]
grid_df = grid_df[(grid_df["ym_int"] >= grid_df["first_ym"]) &
                   (grid_df["ym_int"] <= grid_df["last_ym"])].copy()
grid_df = grid_df.drop(columns=["first_year", "first_month", "last_year",
                                  "last_month", "first_ym", "last_ym", "ym_int"])

# Merge observed coverage into the grid
grid_df = grid_df.merge(df_all[["station_id", "year", "month", "completeness_pct", "quality_flag"]],
                         on=["station_id", "year", "month"], how="left")
# ABSENT where no record was found
grid_df["quality_flag"] = grid_df["quality_flag"].fillna("ABSENT")
grid_df["completeness_pct"] = grid_df["completeness_pct"].fillna(0.0)

print(f"  Full grid (with ABSENT): {len(grid_df)} station-months")

# ── Scorecard ─────────────────────────────────────────────────────────────────
def build_scorecard(gdf):
    rows = []
    for sid, grp in gdf.groupby("station_id"):
        n_total = len(grp)
        n_complete = (grp["quality_flag"] == "COMPLETE").sum()
        n_pm = (grp["quality_flag"] == "PARTIAL_MINOR").sum()
        n_pmaj = (grp["quality_flag"] == "PARTIAL_MAJOR").sum()
        n_sparse = (grp["quality_flag"] == "SPARSE").sum()
        n_absent = (grp["quality_flag"] == "ABSENT").sum()
        pct_complete = n_complete / n_total if n_total > 0 else 0
        pct_any = (n_total - n_absent) / n_total if n_total > 0 else 0
        missingness_rate = 1 - pct_complete

        if pct_complete >= 0.90:
            style = "always_on"
        elif pct_complete >= 0.70:
            style = "occasional_gap"
        elif pct_complete >= 0.40:
            style = "seasonal_dropout"
        else:
            style = "chronic_sparse"

        rows.append({
            "station_id": sid,
            "n_months_total": n_total,
            "n_complete": int(n_complete),
            "n_partial_minor": int(n_pm),
            "n_partial_major": int(n_pmaj),
            "n_sparse": int(n_sparse),
            "n_absent": int(n_absent),
            "pct_complete": round(pct_complete, 4),
            "pct_any_data": round(pct_any, 4),
            "missingness_rate": round(missingness_rate, 4),
            "outage_style": style,
        })
    return pd.DataFrame(rows)

scorecard = build_scorecard(grid_df)
scorecard.to_csv(OUT_DIR / "station_missingness_scorecard.csv", index=False)
print(f"  Saved station_missingness_scorecard.csv ({len(scorecard)} rows)")
print(f"  Outage style distribution:\n{scorecard['outage_style'].value_counts().to_string()}")

# ── Task 2: Run-length analysis ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("TASK 2: Run-length analysis of outages")
print("=" * 70)

def compute_run_lengths(gdf):
    """Return list of run lengths (in months) of ABSENT or SPARSE per station."""
    runs = []
    for sid, grp in gdf.groupby("station_id"):
        seq = grp.sort_values(["year", "month"])["quality_flag"].tolist()
        for flag, group in groupby(seq):
            length = sum(1 for _ in group)
            if flag in ("ABSENT", "SPARSE"):
                runs.append(length)
    return runs

run_lengths = compute_run_lengths(grid_df)
run_arr = np.array(run_lengths)
print(f"  Total outage runs: {len(run_arr)}")
print(f"  Run length stats: min={run_arr.min()}, median={np.median(run_arr):.0f}, "
      f"mean={run_arr.mean():.1f}, max={run_arr.max()}")

bins_rl = [1, 2, 4, 7, run_arr.max() + 1]
labels_rl = ["1 month", "2-3 months", "4-6 months", f">6 months"]
counts_rl = np.histogram(run_arr, bins=bins_rl)[0]
print(f"  Run length distribution: {dict(zip(labels_rl, counts_rl))}")

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(labels_rl, counts_rl, color=["#2196F3", "#FFC107", "#FF5722", "#9C27B0"], edgecolor="white")
ax.set_xlabel("Outage Run Length", fontsize=12)
ax.set_ylabel("Number of Runs", fontsize=12)
ax.set_title("Distribution of Consecutive Absent/Sparse Month Run Lengths\n(All Stations, 2017–2024)", fontsize=13)
for i, v in enumerate(counts_rl):
    ax.text(i, v + max(counts_rl) * 0.01, str(v), ha="center", fontsize=10)
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_run_length_distribution.png", dpi=150)
plt.close()
print("  Saved fig_run_length_distribution.png")

# ── Task 3: Year-over-year missingness trend ──────────────────────────────────
print("\n" + "=" * 70)
print("TASK 3: Year-over-year missingness trend")
print("=" * 70)

yearly = (grid_df.groupby("year")
          .apply(lambda x: 1 - (x["quality_flag"] == "COMPLETE").sum() / len(x))
          .reset_index())
yearly.columns = ["year", "mean_missingness_rate"]
print(f"  Yearly missingness:\n{yearly.to_string(index=False)}")

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(yearly["year"], yearly["mean_missingness_rate"] * 100,
        marker="o", linewidth=2, color="#1565C0", markersize=8)
ax.fill_between(yearly["year"], yearly["mean_missingness_rate"] * 100,
                alpha=0.15, color="#1565C0")
ax.set_xlabel("Year", fontsize=12)
ax.set_ylabel("Mean Missingness Rate (%)", fontsize=12)
ax.set_title("Year-over-Year Mean Station Missingness Rate (2017–2024)", fontsize=13)
ax.set_xticks(yearly["year"])
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
for _, row in yearly.iterrows():
    ax.annotate(f"{row['mean_missingness_rate']*100:.1f}%",
                xy=(row["year"], row["mean_missingness_rate"] * 100),
                xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_missingness_by_year.png", dpi=150)
plt.close()
print("  Saved fig_missingness_by_year.png")

# ── Task 4: Missingness by FC and urban/rural ─────────────────────────────────
print("\n" + "=" * 70)
print("TASK 4: Missingness by functional class and urban/rural")
print("=" * 70)

sc_master = scorecard.merge(
    master[["station_id", "functional_class", "fc_urban_rural"]],
    on="station_id", how="left"
)

# FC summary
fc_summary = (sc_master.groupby("functional_class")["missingness_rate"]
              .agg(["mean", "median", "count"]).reset_index()
              .sort_values("mean", ascending=False))
print(f"  FC missingness:\n{fc_summary.to_string(index=False)}")

# Urban/Rural: extract from fc_urban_rural or functional_class
sc_master["urban_rural"] = sc_master["fc_urban_rural"].apply(
    lambda x: "Urban" if isinstance(x, str) and "Urban" in x else (
              "Rural" if isinstance(x, str) and "Rural" in x else "Unknown"))
ur_summary = (sc_master.groupby("urban_rural")["missingness_rate"]
              .agg(["mean", "median", "count"]).reset_index())
print(f"  Urban/Rural missingness:\n{ur_summary.to_string(index=False)}")

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# FC bar chart
fc_plot = fc_summary.copy()
fc_plot["fc_short"] = fc_plot["functional_class"].apply(
    lambda x: str(x).split(":")[0].strip() if pd.notna(x) else "Unknown")
colors_fc = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(fc_plot)))
bars = axes[0].barh(fc_plot["fc_short"], fc_plot["mean"] * 100,
                    color=colors_fc, edgecolor="white")
axes[0].set_xlabel("Mean Missingness Rate (%)", fontsize=11)
axes[0].set_title("Missingness by Functional Class", fontsize=12)
for bar, val in zip(bars, fc_plot["mean"]):
    axes[0].text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                 f"{val*100:.1f}%", va="center", fontsize=9)

# Urban/Rural bar
ur_plot = ur_summary[ur_summary["urban_rural"] != "Unknown"].copy()
bar_colors = {"Urban": "#1976D2", "Rural": "#388E3C"}
bar_c = [bar_colors.get(u, "#757575") for u in ur_plot["urban_rural"]]
axes[1].bar(ur_plot["urban_rural"], ur_plot["mean"] * 100, color=bar_c, edgecolor="white", width=0.5)
axes[1].set_ylabel("Mean Missingness Rate (%)", fontsize=11)
axes[1].set_title("Missingness by Urban vs. Rural", fontsize=12)
for i, (_, row) in enumerate(ur_plot.iterrows()):
    axes[1].text(i, row["mean"] * 100 + 0.3, f"{row['mean']*100:.1f}%\n(n={int(row['count'])})",
                 ha="center", fontsize=10)

plt.suptitle("Station Missingness by Functional Class and Urban/Rural Classification",
             fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_missingness_by_fc.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved fig_missingness_by_fc.png")

# ── Task 5: Heatmap (station × month) ────────────────────────────────────────
print("\n" + "=" * 70)
print("TASK 5: Station × month missingness heatmap")
print("=" * 70)

# Select top 80 stations by total missing months
missing_per_station = (grid_df[grid_df["quality_flag"].isin(["ABSENT", "SPARSE", "PARTIAL_MAJOR"])]
                        .groupby("station_id").size().reset_index(name="n_missing"))
top80 = missing_per_station.nlargest(80, "n_missing")["station_id"].tolist()
print(f"  Selected {len(top80)} stations for heatmap")

hm_df = grid_df[grid_df["station_id"].isin(top80)].copy()
hm_df["ym_str"] = hm_df["year"].astype(str) + "-" + hm_df["month"].astype(str).str.zfill(2)

# Numeric encoding: COMPLETE=0, PARTIAL_MINOR=0.25, PARTIAL_MAJOR=0.5, SPARSE=0.75, ABSENT=1
flag_map = {"COMPLETE": 0, "PARTIAL_MINOR": 0.25, "PARTIAL_MAJOR": 0.5,
            "SPARSE": 0.75, "ABSENT": 1.0}
hm_df["flag_num"] = hm_df["quality_flag"].map(flag_map)

pivot = hm_df.pivot_table(index="station_id", columns="ym_str",
                           values="flag_num", aggfunc="mean")
# Sort columns chronologically
pivot = pivot.reindex(sorted(pivot.columns), axis=1)
# Sort rows by mean missingness
pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]

fig_h = max(12, len(top80) * 0.18)
fig, ax = plt.subplots(figsize=(22, fig_h))
cmap = mcolors.LinearSegmentedColormap.from_list(
    "miss", ["#1A9850", "#91CF60", "#FEE08B", "#FC8D59", "#D73027"])
im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0, vmax=1,
               interpolation="nearest")
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index, fontsize=6)
# X-axis: show every 6th label
x_labels = list(pivot.columns)
x_ticks = list(range(0, len(x_labels), 6))
ax.set_xticks(x_ticks)
ax.set_xticklabels([x_labels[i] for i in x_ticks], rotation=45, ha="right", fontsize=7)
ax.set_xlabel("Year-Month", fontsize=10)
ax.set_ylabel("Station ID", fontsize=10)
ax.set_title("Missingness Heatmap: Top 80 Stations by Missing Months (2017–2024)\n"
             "Green=Complete, Yellow=Partial, Orange=Sparse, Red=Absent", fontsize=11)
cbar = plt.colorbar(im, ax=ax, orientation="vertical", fraction=0.02, pad=0.02)
cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
cbar.set_ticklabels(["Complete", "Partial Minor", "Partial Major", "Sparse", "Absent"])
cbar.ax.tick_params(labelsize=8)
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_missingness_by_station_heatmap.png", dpi=120, bbox_inches="tight")
plt.close()
print("  Saved fig_missingness_by_station_heatmap.png")

# ── Task 6 & 7: Hour-of-day / DOW bias from 2024 raw data ────────────────────
print("\n" + "=" * 70)
print("TASK 6 & 7: Hour-of-day and day-of-week bias (2024 sample)")
print("=" * 70)

# Get available COSITs from 2024 directory
available_data1 = sorted(CCS_2024_DIR.glob("GDOT_CCS-*-data-1.csv"))
available_cosits_raw = [f.name.split("-data-1")[0].replace("GDOT_CCS-", "") for f in available_data1]
# Strip leading zeros to numeric for matching
available_cosit_set = set(str(int(c)) for c in available_cosits_raw)
cosit_file_map = {str(int(c)): f for c, f in zip(available_cosits_raw, available_data1)}
print(f"  Available 2024 data-1 files: {len(available_data1)}")

# Get station master with cosit
master_cosit = master.dropna(subset=["cosit"]).copy()
master_cosit["cosit_str"] = master_cosit["cosit"].astype(int).astype(str)
master_cosit = master_cosit[master_cosit["cosit_str"].isin(available_cosit_set)].copy()
print(f"  Stations with 2024 data available: {len(master_cosit)}")

# Stratified sample: across FC categories
fc_groups = master_cosit.groupby("functional_class")
sample_dfs = []
target_total = 50
for fc, grp in fc_groups:
    n = max(1, round(target_total * len(grp) / len(master_cosit)))
    sample_dfs.append(grp.sample(min(n, len(grp)), random_state=42))
sampled = pd.concat(sample_dfs).drop_duplicates("station_id").head(target_total)
print(f"  Sampled {len(sampled)} stations across {sampled['functional_class'].nunique()} FC categories")
print(f"  FC breakdown:\n{sampled['functional_class'].value_counts().to_string()}")

# Analyze each station
hourly_miss = np.zeros(24)
hourly_total = np.zeros(24)
dow_miss = np.zeros(7)
dow_total = np.zeros(7)
n_zero_volume = 0
n_impossible = 0
n_total_rows = 0
n_processed = 0

for _, row in sampled.iterrows():
    cosit_str = str(int(row["cosit"]))
    fpath = cosit_file_map.get(cosit_str)
    if fpath is None:
        continue
    try:
        df = pd.read_csv(fpath, low_memory=False)
    except Exception as e:
        print(f"    Could not read {fpath.name}: {e}")
        continue

    # Parse time
    df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
    df = df.dropna(subset=["Start Time"])
    if len(df) == 0:
        continue

    df["hour"] = df["Start Time"].dt.hour
    df["dow"] = df["Start Time"].dt.dayofweek  # 0=Mon
    df["cov"] = pd.to_numeric(df["Coverage %"], errors="coerce").fillna(0)
    df["cnt"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)

    # Missing: coverage == 0 (sensor inactive / truly absent bin)
    df["is_missing"] = df["cov"] == 0

    n_total_rows += len(df)
    n_processed += 1

    # Hourly aggregation
    for h in range(24):
        mask_h = df["hour"] == h
        hourly_total[h] += mask_h.sum()
        hourly_miss[h] += (df.loc[mask_h, "is_missing"]).sum()

    # DOW aggregation
    for d in range(7):
        mask_d = df["dow"] == d
        dow_total[d] += mask_d.sum()
        dow_miss[d] += (df.loc[mask_d, "is_missing"]).sum()

    # Task 7: zero-volume detection
    zero_vol = ((df["cnt"] == 0) & (df["cov"] > 50)).sum()
    impossible = ((df["cov"] > 100) | (df["cnt"] < 0)).sum()
    n_zero_volume += zero_vol
    n_impossible += impossible

print(f"  Processed {n_processed} station files, {n_total_rows:,} total 5-min records")
print(f"  Zero-volume records (Count=0, Coverage>50%): {n_zero_volume:,} "
      f"({100*n_zero_volume/max(n_total_rows,1):.2f}%)")
print(f"  Impossible records (Coverage>100 or Count<0): {n_impossible:,}")

# Hourly bias plot
with np.errstate(divide="ignore", invalid="ignore"):
    hourly_rate = np.where(hourly_total > 0, hourly_miss / hourly_total, np.nan)
    dow_rate = np.where(dow_total > 0, dow_miss / dow_total, np.nan)

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(range(24), hourly_rate * 100, color="#1565C0", edgecolor="white", alpha=0.85)
ax.set_xlabel("Hour of Day (0 = midnight)", fontsize=12)
ax.set_ylabel("Mean Fraction of Missing 5-min Bins (%)", fontsize=11)
ax.set_title(f"Hour-of-Day Missingness Bias\n(Coverage%=0, stratified sample of {n_processed} stations, 2024 data)",
             fontsize=12)
ax.set_xticks(range(24))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_hourly_bias_sample.png", dpi=150)
plt.close()
print("  Saved fig_hourly_bias_sample.png")

# DOW bias plot
dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
fig, ax = plt.subplots(figsize=(8, 5))
colors_dow = ["#1565C0"] * 5 + ["#E53935", "#E53935"]
ax.bar(dow_labels, dow_rate * 100, color=colors_dow, edgecolor="white", alpha=0.85)
ax.set_xlabel("Day of Week", fontsize=12)
ax.set_ylabel("Mean Fraction of Missing 5-min Bins (%)", fontsize=11)
ax.set_title(f"Day-of-Week Missingness Bias\n(Coverage%=0, stratified sample of {n_processed} stations, 2024 data)",
             fontsize=12)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}%"))
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_dow_bias_sample.png", dpi=150)
plt.close()
print("  Saved fig_dow_bias_sample.png")

# ── Task 8: Outage classification summary ─────────────────────────────────────
print("\n" + "=" * 70)
print("TASK 8: Outage classification summary")
print("=" * 70)

style_counts = scorecard.groupby("outage_style").agg(
    n_stations=("station_id", "count"),
    example_stations=("station_id", lambda x: "; ".join(list(x[:3])))
).reset_index()
total_s = style_counts["n_stations"].sum()
style_counts["pct_of_total"] = (style_counts["n_stations"] / total_s * 100).round(2)
style_counts.to_csv(OUT_DIR / "outage_classification_summary.csv", index=False)
print(f"  Saved outage_classification_summary.csv")
print(style_counts.to_string(index=False))

# ── Verify outputs ────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("OUTPUT VERIFICATION")
print("=" * 70)

required = [
    "station_missingness_scorecard.csv",
    "station_month_issue_table.csv",
    "outage_classification_summary.csv",
    "fig_missingness_by_station_heatmap.png",
    "fig_run_length_distribution.png",
    "fig_missingness_by_year.png",
    "fig_missingness_by_fc.png",
    "fig_hourly_bias_sample.png",
    "fig_dow_bias_sample.png",
]
all_ok = True
for fname in required:
    fpath = OUT_DIR / fname
    if fpath.exists():
        size = fpath.stat().st_size
        print(f"  OK  {fname:50s} {size:>10,} bytes")
    else:
        print(f"  MISSING  {fname}")
        all_ok = False

print(f"\n{'All outputs verified.' if all_ok else 'Some outputs MISSING.'}")

# ── Collect summary stats for report ─────────────────────────────────────────
n_stations_total = scorecard["station_id"].nunique()
n_station_months = len(grid_df)
n_complete_sm = (grid_df["quality_flag"] == "COMPLETE").sum()
n_absent_sm = (grid_df["quality_flag"] == "ABSENT").sum()
overall_missingness = 1 - n_complete_sm / n_station_months

pct_always_on = style_counts.loc[style_counts["outage_style"] == "always_on", "pct_of_total"].values
pct_chronic = style_counts.loc[style_counts["outage_style"] == "chronic_sparse", "pct_of_total"].values
pct_always_on = pct_always_on[0] if len(pct_always_on) > 0 else 0
pct_chronic = pct_chronic[0] if len(pct_chronic) > 0 else 0

median_rl = float(np.median(run_arr))
max_rl = int(run_arr.max())
n_long_outages = int((run_arr > 6).sum())

peak_missing_hour = int(np.nanargmax(hourly_rate))
min_missing_hour = int(np.nanargmin(hourly_rate))
peak_missing_dow = dow_labels[int(np.nanargmax(dow_rate))]

# Write summary data to a temp file for report
import json

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

summary_data = {
    "n_stations_total": n_stations_total,
    "n_station_months": n_station_months,
    "n_complete_sm": int(n_complete_sm),
    "n_absent_sm": int(n_absent_sm),
    "overall_missingness_pct": round(overall_missingness * 100, 2),
    "pct_always_on": float(pct_always_on),
    "pct_chronic": float(pct_chronic),
    "median_run_length": median_rl,
    "max_run_length": max_rl,
    "n_long_outages": n_long_outages,
    "n_processed_stations_2024": n_processed,
    "n_total_rows_2024": n_total_rows,
    "n_zero_volume": n_zero_volume,
    "zero_vol_pct": round(100 * n_zero_volume / max(n_total_rows, 1), 2),
    "n_impossible": n_impossible,
    "peak_missing_hour": peak_missing_hour,
    "min_missing_hour": min_missing_hour,
    "peak_missing_dow": peak_missing_dow,
    "run_length_distribution": dict(zip(labels_rl, [int(x) for x in counts_rl])),
    "style_counts": style_counts.to_dict(orient="records"),
    "yearly_missingness": yearly.to_dict(orient="records"),
    "fc_summary": fc_summary.to_dict(orient="records"),
}
with open(OUT_DIR / "_summary_data.json", "w") as f:
    json.dump(summary_data, f, indent=2, cls=NpEncoder)

print("\nAll tasks complete. Summary data saved.")
print(f"Overall missingness rate: {overall_missingness*100:.1f}%")
print(f"Stations: {n_stations_total}, Station-months: {n_station_months:,}")
