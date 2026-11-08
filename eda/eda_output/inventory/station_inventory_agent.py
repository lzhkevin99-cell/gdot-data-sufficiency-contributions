"""
station_inventory_agent.py
GDOT EDA Workflow — Station Inventory & Master Table Builder

Outputs to: /Users/kevinli/Desktop/Research_Gtech_gdot/eda_output/inventory/
"""

import os
import re
import glob
import warnings
import textwrap
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path("/Users/kevinli/Desktop/Research_Gtech_gdot")
OUTPUTS     = ROOT / "outputs"
DATA        = ROOT / "gdot_2025_data_total"
OUT_DIR     = ROOT / "eda_output" / "inventory"

DIR_2024    = DATA / "CCS_5Min_2024"
DIR_2022_23 = DATA / "GDOT_CCS_2022-2023"
DIR_2017_22 = DATA / "GDoT_UGA_Directional_Export_2017-2022" / "directional"

OUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"[INIT] Output directory: {OUT_DIR}")


# ── 1. Load station_catalog ───────────────────────────────────────────────────
def load_catalog():
    print("\n[1] Loading station_catalog.csv …")
    df = pd.read_csv(OUTPUTS / "station_catalog.csv", low_memory=False)
    print(f"    Rows: {len(df):,}  Columns: {len(df.columns)}")
    n_unique_cosit       = df["cosit"].nunique()
    n_unique_station_name = df["station_name"].nunique()
    print(f"    Unique cosit values:        {n_unique_cosit:,}")
    print(f"    Unique station_name values: {n_unique_station_name:,}")
    return df


# ── 2. Load & merge completeness CSVs ─────────────────────────────────────────
def load_completeness():
    print("\n[2] Loading completeness CSVs …")

    # 2024 tier  — key col is 'cosit'
    c24 = pd.read_csv(OUTPUTS / "completeness_2024.csv", low_memory=False)
    print(f"    completeness_2024:      {len(c24):,} rows  cols={c24.columns.tolist()}")
    # Normalise: create unified 'station_id' = station_name (already 'station_name' col exists)
    c24 = c24.rename(columns={"station_name": "station_id"})
    c24["tier"] = "5min_2024"

    # 2022-2023 tier — key col is 'station_name'
    c2223 = pd.read_csv(OUTPUTS / "completeness_2022_2023.csv", low_memory=False)
    print(f"    completeness_2022_2023: {len(c2223):,} rows  cols={c2223.columns.tolist()}")
    c2223 = c2223.rename(columns={"station_name": "station_id"})
    c2223["tier"] = "5min_2022_2023"

    # 2017-2022 tier — key col is 'station_name'
    c1722 = pd.read_csv(OUTPUTS / "completeness_2017_2022.csv", low_memory=False)
    print(f"    completeness_2017_2022: {len(c1722):,} rows  cols={c1722.columns.tolist()}")
    c1722 = c1722.rename(columns={"station_name": "station_id"})
    c1722["tier"] = "hist_2017_2022"

    # Align columns — keep common subset + tier
    common = ["station_id", "year", "month", "completeness_pct", "complete", "tier"]
    for df in [c24, c2223, c1722]:
        for col in common:
            if col not in df.columns:
                df[col] = None

    merged = pd.concat([c24[common], c2223[common], c1722[common]], ignore_index=True)
    merged["year"]  = pd.to_numeric(merged["year"],  errors="coerce")
    merged["month"] = pd.to_numeric(merged["month"], errors="coerce")
    merged["completeness_pct"] = pd.to_numeric(merged["completeness_pct"], errors="coerce")
    merged["complete"] = merged["complete"].map(
        {True: True, False: False, "True": True, "False": False}
    ).fillna(False)
    # Build a date column for first/last
    merged["date"] = pd.to_datetime(
        merged["year"].astype("Int64").astype(str) + "-" +
        merged["month"].astype("Int64").astype(str).str.zfill(2) + "-01",
        errors="coerce"
    )
    print(f"    Combined completeness rows: {len(merged):,}")
    return merged, c24, c2223, c1722


# ── 3. Per-station aggregation ────────────────────────────────────────────────
def aggregate_completeness(merged):
    print("\n[3] Aggregating completeness per station …")
    grp = merged.groupby("station_id")
    agg = pd.DataFrame({
        "total_months_available": grp.size(),
        "complete_months":        grp["complete"].sum(),
        "first_date":             grp["date"].min(),
        "last_date":              grp["date"].max(),
    }).reset_index()
    agg["incomplete_months"] = agg["total_months_available"] - agg["complete_months"]
    # Which tiers
    tier_flags = merged.groupby("station_id")["tier"].apply(set).reset_index()
    tier_flags.columns = ["station_id", "tiers_set"]
    agg = agg.merge(tier_flags, on="station_id", how="left")
    print(f"    Stations with completeness data: {len(agg):,}")
    return agg


# ── 4. Station-source cross-tab ────────────────────────────────────────────────
def source_crosstab(catalog_df):
    print("\n[4] Station-source cross-tab …")
    sp = pd.read_csv(OUTPUTS / "station_source_presence.csv", low_memory=False)
    print(f"    station_source_presence rows: {len(sp):,}")
    print(f"    Columns: {sp.columns.tolist()}")
    n_all3  = (sp["n_sources"] == 3).sum()
    n_two   = (sp["n_sources"] == 2).sum()
    n_one   = (sp["n_sources"] == 1).sum()
    print(f"    In all 3 tiers:     {n_all3:,}")
    print(f"    In exactly 2 tiers: {n_two:,}")
    print(f"    In exactly 1 tier:  {n_one:,}")
    return sp, {"all_3": int(n_all3), "exactly_2": int(n_two), "exactly_1": int(n_one)}


# ── 5. Metadata null audit ────────────────────────────────────────────────────
def metadata_null_audit(catalog_df):
    print("\n[5] Metadata null audit (columns > 10% null) …")
    null_pct = (catalog_df.isnull().mean() * 100).sort_values(ascending=False)
    high_null = null_pct[null_pct > 10].reset_index()
    high_null.columns = ["column", "null_pct"]
    print(f"    Columns with >10% null: {len(high_null)}")
    print(high_null.to_string(index=False))
    return high_null


# ── 6. Functional class distribution chart ────────────────────────────────────
def fig_functional_class(catalog_df):
    print("\n[6] Functional class distribution chart …")
    col = "functional_class"
    if col not in catalog_df.columns:
        print(f"    WARNING: column '{col}' not found. Skipping.")
        return
    counts = catalog_df[col].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    counts.plot(kind="bar", ax=ax, color="#2b7bba", edgecolor="white")
    ax.set_title("Station Count by Functional Class", fontsize=13)
    ax.set_xlabel("Functional Class")
    ax.set_ylabel("Number of Stations")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    out = OUT_DIR / "fig_functional_class.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"    Saved: {out}")


# ── 7. Urban/rural pie chart ──────────────────────────────────────────────────
def fig_urban_rural(catalog_df):
    print("\n[7] Urban/rural pie chart …")
    col = "fc_urban_rural"
    if col not in catalog_df.columns:
        # try fallback
        col = "urban_area_type"
    if col not in catalog_df.columns:
        print(f"    WARNING: no urban/rural column found. Skipping.")
        return
    counts = catalog_df[col].fillna("Unknown").value_counts()
    fig, ax = plt.subplots(figsize=(7, 7))
    wedge_props = {"edgecolor": "white", "linewidth": 1.5}
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%",
           startangle=140, wedgeprops=wedge_props)
    ax.set_title("Urban / Rural Breakdown of Stations", fontsize=13)
    plt.tight_layout()
    out = OUT_DIR / "fig_urban_rural.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"    Saved: {out}")


# ── 8. Schema audit ───────────────────────────────────────────────────────────
def schema_audit():
    print("\n[8] Schema audit …")
    notes = []

    def read_sample(path, nrows=5):
        try:
            df = pd.read_csv(path, nrows=nrows)
            return df
        except Exception as e:
            return str(e)

    # 3 sample files from CCS_5Min_2024
    data1_files = sorted(glob.glob(str(DIR_2024 / "*-data-1.csv")))[:3]
    tier2024_schemas = []
    notes.append("=" * 70)
    notes.append("TIER 1: CCS_5Min_2024  (5-minute intervals, per-direction bins)")
    notes.append("=" * 70)
    for fp in data1_files:
        df = read_sample(fp)
        if isinstance(df, str):
            notes.append(f"  ERROR reading {fp}: {df}")
            continue
        cosit = re.search(r"GDOT_CCS-(\d+)-data", Path(fp).name)
        cosit_str = cosit.group(1) if cosit else "unknown"
        notes.append(f"\n  File: {Path(fp).name}")
        notes.append(f"  COSIT (from filename): {cosit_str}")
        notes.append(f"  Columns ({len(df.columns)}): {df.columns.tolist()}")
        notes.append(f"  Dtypes: {df.dtypes.to_dict()}")
        notes.append(f"  Time column: 'Start Time'  Sample value: {df['Start Time'].iloc[0] if 'Start Time' in df.columns else 'N/A'}")
        notes.append(f"  Station ID: embedded in filename as numeric COSIT (12-digit zero-padded)")
        tier2024_schemas.append(set(df.columns.tolist()))

    # 1 sample from GDOT_CCS_2022-2023
    notes.append("\n" + "=" * 70)
    notes.append("TIER 2: GDOT_CCS_2022-2023  (5-minute bins, per-lane)")
    notes.append("=" * 70)
    fp2 = sorted(glob.glob(str(DIR_2022_23 / "*.csv")))[0]
    df2 = read_sample(fp2)
    if not isinstance(df2, str):
        notes.append(f"\n  File: {Path(fp2).name}")
        notes.append(f"  Columns ({len(df2.columns)}): {df2.columns.tolist()}")
        notes.append(f"  Dtypes: {df2.dtypes.to_dict()}")
        notes.append(f"  Time column: 'Time'  Sample value: {df2['Time'].iloc[0] if 'Time' in df2.columns else 'N/A'}")
        notes.append(f"  Station ID: 'Site' column, format 'XXX-XXXX' (e.g. 001-0183), quoted string")

    # 1 sample from GDoT_UGA_Directional_Export_2017-2022
    notes.append("\n" + "=" * 70)
    notes.append("TIER 3: GDoT_UGA_Directional_Export_2017-2022  (hourly bins, directional)")
    notes.append("=" * 70)
    fp3 = sorted(glob.glob(str(DIR_2017_22 / "*.csv")))[0]
    df3 = read_sample(fp3)
    if not isinstance(df3, str):
        notes.append(f"\n  File: {Path(fp3).name}")
        notes.append(f"  Columns ({len(df3.columns)}): {df3.columns.tolist()}")
        notes.append(f"  Dtypes: {df3.dtypes.to_dict()}")
        notes.append(f"  Time column: 'Time'  Sample value: {df3['Time'].iloc[0] if 'Time' in df3.columns else 'N/A'}")
        notes.append(f"  Station ID: 'Site' column, format 'XXX-XXXX', quoted string")

    # Summary of differences
    notes.append("\n" + "=" * 70)
    notes.append("KEY SCHEMA DIFFERENCES SUMMARY")
    notes.append("=" * 70)
    notes.append("""
1. Station ID format:
   - Tier 1 (2024):      12-digit zero-padded numeric COSIT in filename
                         e.g., 000000010183  → station_name '001-0183'
   - Tier 2 (2022-2023): 'Site' column, string format 'XXX-XXXX'
                         e.g., '001-0183'
   - Tier 3 (2017-2022): 'Site' column, string format 'XXX-XXXX'
                         e.g., '001-0183'
   → Tiers 2 & 3 are directly joinable; Tier 1 requires mapping cosit→station_name.

2. Time column name:
   - Tier 1: 'Start Time' (and 'End Time'), format YYYY-MM-DD HH:MM:SS (5-min)
   - Tier 2: 'Time', format YYYY-MM-DD HH:MM:SS (5-min intervals)
   - Tier 3: 'Time', format YYYY-MM-DD HH:MM:SS (hourly intervals, BinDuration=3600)

3. Temporal resolution (BinDuration):
   - Tier 1: 5-minute (300 s implied; no BinDuration column in data-1.csv)
   - Tier 2: 300 s (5-minute); has 'BinDuration' column
   - Tier 3: 3600 s (hourly);  has 'BinDuration' column

4. Stratification dimension:
   - Tier 1: 'Direction' column (N/S/E/W)
   - Tier 2: 'Lane' column (e.g., 'Ln 1 NB') — per-lane data
   - Tier 3: 'Direction' column (N/S/E/W) — directional aggregates

5. Speed breakdown:
   - Tier 1: Has speed bin columns (<10 mph, 10-20 mph, … >80 mph)
             and axle-weight bins (<6000 lb … >130000 lb)
   - Tier 2: No AvgSpeed or speed bins (classification only: F1-F15)
   - Tier 3: Has 'AvgSpeed' column; no per-bin speed breakdown

6. QC flags:
   - Tier 1: 'Coverage %' per interval
   - Tier 2: No QC columns in raw monthly files (QC in metadata)
   - Tier 3: 'VolumeQC', 'ClassQC' columns

7. Length/weight data:
   - Tier 1: Length bins (<7 ft, 7-22 ft, 22-48 ft, >48 ft) and weight bins present
   - Tier 2: F1-F15 vehicle class counts only
   - Tier 3: F1-F15 vehicle class counts only
""")

    txt = "\n".join(notes)
    out = OUT_DIR / "schema_audit_notes.txt"
    out.write_text(txt)
    print(f"    Saved: {out}")
    return txt


# ── 9. Duplicate / non-standard station IDs ───────────────────────────────────
def check_nonstandard_ids(catalog_df, presence_df):
    print("\n[9] Checking for non-standard station IDs …")
    # From station_source_presence (uses station_name format)
    ids = presence_df["station"].astype(str)
    # Pattern: standard is DDD-DDDD  (e.g. 001-0183)
    standard = ids.str.match(r"^\d{3}-\d{4}$")
    non_standard = ids[~standard]
    n_w = ids[ids.str.contains("w", case=False, na=False)].shape[0]
    print(f"    Total station IDs in source_presence: {len(ids):,}")
    print(f"    Standard (DDD-DDDD) format:           {standard.sum():,}")
    print(f"    Non-standard IDs:                     {len(non_standard):,}")
    print(f"    IDs containing 'w' (e.g. 021-w334):   {n_w:,}")
    if len(non_standard) > 0:
        print(f"    Sample non-standard: {non_standard.head(10).tolist()}")
    return {
        "total_ids": len(ids),
        "standard_count": int(standard.sum()),
        "non_standard_count": len(non_standard),
        "w_format_count": int(n_w),
        "non_standard_examples": non_standard.head(10).tolist()
    }


# ── 10. Build station_master_table ─────────────────────────────────────────────
def build_master_table(catalog_df, agg_comp, presence_df):
    print("\n[10] Building station_master_table …")

    # Catalog: keep key metadata
    cat = catalog_df[["cosit", "station_name", "functional_class", "fc_urban_rural",
                       "county", "district", "latitude", "longitude"]].copy()
    cat["cosit"] = cat["cosit"].astype(str).str.strip()
    cat["station_name"] = cat["station_name"].astype(str).str.strip()

    # Presence: station_id = station_name format (XXX-XXXX)
    pres = presence_df.rename(columns={"station": "station_id"}).copy()
    pres["station_id"] = pres["station_id"].astype(str).str.strip()

    # Completeness agg: station_id = station_name format
    comp = agg_comp.copy()
    comp["station_id"] = comp["station_id"].astype(str).str.strip()

    # Merge presence + completeness
    master = pres.merge(comp, on="station_id", how="outer")

    # Join catalog metadata: try station_id == station_name first
    merged = master.merge(cat, left_on="station_id", right_on="station_name", how="left")
    matched = merged["cosit"].notna().sum()
    print(f"    Matched to catalog via station_name: {matched:,} / {len(merged):,}")

    # For unmatched rows, try to derive station_name from cosit pattern
    # (station_name format is 'XXX-XXXX' which is cosit digits 5-7 and 8-11)
    unmatched_mask = merged["cosit"].isna()
    if unmatched_mask.sum() > 0:
        # Try matching completeness 'cosit' col back if available (c24 has cosit)
        # Build a cosit→station_name map from catalog
        cosit_map = cat.set_index("cosit")["station_name"].to_dict()
        # For 5min_2024 tier, completeness has 'cosit' — but after aggregation we lost it
        # Best effort: convert station_id back to cosit pattern
        # station_id like '001-0183' → derive cosit by zero-padding: 000000010183
        def station_to_cosit(sid):
            m = re.match(r"^(\d{3})-(\d{4})$", str(sid))
            if m:
                return f"{int(m.group(1)):06d}{int(m.group(2)):06d}"
            return None
        derived = merged.loc[unmatched_mask, "station_id"].apply(station_to_cosit)
        for idx, cosit_derived in derived.items():
            if cosit_derived and cosit_derived in cosit_map:
                # fill from catalog
                row = cat[cat["cosit"] == cosit_derived].iloc[0]
                merged.loc[idx, "cosit"] = row["cosit"]
                merged.loc[idx, "station_name"] = row["station_name"]
                for col in ["functional_class", "fc_urban_rural", "county", "district", "latitude", "longitude"]:
                    merged.loc[idx, col] = row[col]
        matched2 = merged["cosit"].notna().sum()
        print(f"    After cosit-derive fallback: {matched2:,} / {len(merged):,} matched")

    # Drop duplicate station_name column from merge
    if "station_name" in merged.columns:
        merged = merged.drop(columns=["station_name"])

    # Rename/select final columns
    final_cols = [
        "station_id", "cosit", "functional_class", "fc_urban_rural",
        "county", "district", "latitude", "longitude",
        "in_hist_2017_2022", "in_5min_2022_2023", "in_5min_2024", "n_sources",
        "total_months_available", "complete_months", "incomplete_months",
        "first_date", "last_date"
    ]
    for c in final_cols:
        if c not in merged.columns:
            merged[c] = None

    master_final = merged[final_cols].copy()
    master_final = master_final.drop_duplicates(subset=["station_id"])
    master_final = master_final.sort_values("station_id").reset_index(drop=True)

    out = OUT_DIR / "station_master_table.csv"
    master_final.to_csv(out, index=False)
    print(f"    station_master_table rows: {len(master_final):,}")
    print(f"    Saved: {out}")
    return master_final


# ── 11. Data source overlap figure ────────────────────────────────────────────
def fig_data_source_overlap(presence_df, xtab_counts):
    print("\n[11] Data source overlap bar chart …")
    sp = presence_df.copy()
    # Create combination label
    def combo_label(row):
        parts = []
        if row.get("in_hist_2017_2022", False): parts.append("2017-2022")
        if row.get("in_5min_2022_2023", False):  parts.append("2022-2023")
        if row.get("in_5min_2024",      False):  parts.append("2024")
        return " + ".join(parts) if parts else "None"

    sp["combo"] = sp.apply(combo_label, axis=1)
    counts = sp["combo"].value_counts().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#bcbd22"]
    bars = ax.bar(range(len(counts)), counts.values,
                  color=colors[:len(counts)], edgecolor="white")
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=30, ha="right", fontsize=9)
    ax.set_title("Station Count by Data Source Combination", fontsize=13)
    ax.set_xlabel("Source Combination")
    ax.set_ylabel("Number of Stations")
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                str(val), ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    out = OUT_DIR / "fig_data_source_overlap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"    Saved: {out}")


# ── 12. Completeness distribution figure ──────────────────────────────────────
def fig_completeness_distribution(merged_comp):
    print("\n[12] Completeness distribution figure …")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
    tiers = [
        ("5min_2024",      "2024 (5-min)",          "#1f77b4"),
        ("5min_2022_2023", "2022-2023 (5-min)",      "#ff7f0e"),
        ("hist_2017_2022", "2017-2022 (Directional)","#2ca02c"),
    ]
    for ax, (tier, label, color) in zip(axes, tiers):
        sub = merged_comp[merged_comp["tier"] == tier]["completeness_pct"].dropna()
        if len(sub) == 0:
            ax.set_title(f"{label}\n(no data)")
            continue
        ax.hist(sub, bins=30, color=color, edgecolor="white", alpha=0.85)
        ax.axvline(80, color="red", linestyle="--", linewidth=1.2, label="80% threshold")
        ax.set_title(f"{label}\nn={len(sub):,}", fontsize=11)
        ax.set_xlabel("Completeness %")
        ax.set_ylabel("Months")
        ax.legend(fontsize=8)
    plt.suptitle("Monthly Completeness Distribution by Data Tier", fontsize=13, y=1.01)
    plt.tight_layout()
    out = OUT_DIR / "fig_completeness_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    Saved: {out}")


# ── 13. Write inventory_summary.md ────────────────────────────────────────────
def write_summary(catalog_df, master_df, merged_comp, xtab, null_audit, id_check):
    print("\n[13] Writing inventory_summary.md …")

    n_catalog   = len(catalog_df)
    n_cosit     = catalog_df["cosit"].nunique()
    n_master    = len(master_df)
    n_with_meta = master_df["cosit"].notna().sum()
    n_all3      = xtab["all_3"]
    n_two       = xtab["exactly_2"]
    n_one       = xtab["exactly_1"]

    # completeness stats
    comp_by_tier = merged_comp.groupby("tier")["completeness_pct"].agg(["mean", "median", "count"])
    comp_str = comp_by_tier.to_string()

    # complete month pcts by tier
    tier_complete = merged_comp.groupby("tier")["complete"].mean() * 100

    # null audit top 10
    null_top10 = null_audit.head(10).to_string(index=False)

    # master table quick stats
    mc_mean = master_df["complete_months"].mean() if "complete_months" in master_df.columns else float("nan")
    mc_med  = master_df["complete_months"].median() if "complete_months" in master_df.columns else float("nan")

    # functional class counts
    fc_counts = catalog_df["functional_class"].value_counts().head(8).to_string()
    ur_counts = catalog_df["fc_urban_rural"].value_counts().to_string()

    content = f"""## Objective

Build a unified station master table and produce inventory outputs for the GDOT traffic counting station dataset, covering three data tiers spanning 2017–2024. This supports the GDOT EDA workflow by characterising station coverage, data completeness, schema differences across tiers, and metadata quality.

---

## Methods

1. **station_catalog.csv** loaded as the canonical station list ({n_catalog:,} rows, {catalog_df["cosit"].nunique():,} unique COSIT values).
2. Three completeness CSVs unioned into a single long-format table keyed by station_id (station_name format `XXX-XXXX`).
3. Per-station aggregation: total months, complete months (where `complete == True`, equivalent to ≥80% bin coverage), first/last date.
4. station_source_presence.csv used for tier membership flags.
5. station_master_table built by joining presence + completeness data to catalog metadata via `station_name` ↔ `station_id` matching.
6. Schema audit performed by reading header + 5 rows from 3 sample CCS_5Min_2024 files, 1 GDOT_CCS_2022-2023 file, and 1 GDoT_UGA_Directional file.
7. Non-standard ID detection via regex matching against `^\\d{{3}}-\\d{{4}}$` pattern.
8. Five figures produced (functional class, urban/rural, source overlap, completeness distributions).

---

## Key Findings

### Station Counts
| Metric | Value |
|---|---|
| Rows in station_catalog | {n_catalog:,} |
| Unique COSIT values in catalog | {n_cosit:,} |
| Stations in master table | {n_master:,} |
| Stations matched to catalog metadata | {n_with_meta:,} |
| Stations in all 3 tiers | {n_all3:,} |
| Stations in exactly 2 tiers | {n_two:,} |
| Stations in exactly 1 tier | {n_one:,} |

### Completeness by Tier
```
{comp_str}
```

Complete month rates (completeness_pct >= 80%):
{tier_complete.to_string()}

### Master Table Completeness Stats
- Mean complete months per station:   {mc_mean:.1f}
- Median complete months per station: {mc_med:.1f}

### Station ID Format Issues
| Metric | Count |
|---|---|
| Total IDs in source presence | {id_check["total_ids"]:,} |
| Standard format (DDD-DDDD) | {id_check["standard_count"]:,} |
| Non-standard IDs | {id_check["non_standard_count"]:,} |
| IDs containing 'w' suffix | {id_check["w_format_count"]:,} |

Non-standard examples: `{id_check["non_standard_examples"]}`

### Metadata Null Audit (top 10 columns by null %)
```
{null_top10}
```

### Functional Class Distribution (top 8)
```
{fc_counts}
```

### Urban/Rural Breakdown
```
{ur_counts}
```

### Schema Key Differences Across Tiers
| Dimension | Tier 1: CCS_5Min_2024 | Tier 2: GDOT_CCS_2022-2023 | Tier 3: GDoT_UGA_Directional_2017-2022 |
|---|---|---|---|
| Station ID | 12-digit COSIT in filename | 'Site' col, `XXX-XXXX` | 'Site' col, `XXX-XXXX` |
| Time column | 'Start Time' | 'Time' | 'Time' |
| Resolution | 5-min (implied) | 5-min (BinDuration=300) | Hourly (BinDuration=3600) |
| Stratification | Direction (N/S/E/W) | Lane (Ln 1 NB etc.) | Direction (N/S/E/W) |
| Speed data | Speed bins (<10 mph…>80 mph) | None | AvgSpeed only |
| Weight data | Weight bins present | None | None |
| QC flags | Coverage % per interval | None in monthly files | VolumeQC, ClassQC |

---

## Tables/Plots Created

| File | Description |
|---|---|
| `station_master_table.csv` | One row per station with metadata + completeness + tier flags |
| `schema_audit_notes.txt` | Detailed schema comparison across all 3 tiers |
| `fig_functional_class.png` | Bar chart of station counts by FHWA functional class |
| `fig_urban_rural.png` | Pie chart of urban vs. rural station distribution |
| `fig_data_source_overlap.png` | Bar chart of station counts by source tier combination |
| `fig_completeness_distribution.png` | Histograms of monthly completeness % per tier |

---

## Risks/Caveats

1. **ID format mismatch**: Tier 1 (2024) uses 12-digit zero-padded numeric COSIT in filenames (`000000010183`), while Tiers 2 & 3 and the completeness CSVs use the `XXX-XXXX` station_name format (`001-0183`). A derivation mapping is applied (padding/unpadding), but edge cases may exist for non-standard IDs.

2. **Non-standard IDs**: {id_check["non_standard_count"]:,} station IDs do not match the `DDD-DDDD` pattern. These may be legacy, WIM, or special-purpose sites. They cannot be reliably cross-referenced without additional lookup tables.

3. **completeness_2024.csv has COSIT column; others have station_name**: The completeness union normalises on station_name format, but the Tier 1 completeness table reports `cosit` as the primary key. Mismatches could cause ~{max(0, n_master - n_with_meta):,} stations to appear with incomplete catalog metadata.

4. **Multiple data files per station in 2024**: Some stations have `data-2.csv`, `data-3.csv`, etc. (possibly from recorder replacements or multi-sensor setups). The completeness metrics may not capture all sub-files.

5. **High null rates in catalog**: Several metadata columns (e.g., Bridge ID, LTPP Site Id, WIM fields) have very high null rates because they are only applicable to specific station types. These are not data quality issues per se.

6. **Hourly vs. 5-minute resolution**: Tier 3 data (2017-2022) is hourly, making direct bin-count comparisons with Tiers 1 & 2 inappropriate without resampling.

---

## Recommended Next Steps

1. **Reconcile the COSIT ↔ station_name mapping** systematically: build a definitive lookup table from `station_catalog.csv` (`cosit` → `station_name`) and apply it as the canonical join key across all tiers.

2. **Investigate non-standard station IDs** (n={id_check["non_standard_count"]}): determine if 'w'-suffixed IDs correspond to WIM stations or legacy codes; add a `station_type` flag to the master table.

3. **Gap-fill analysis**: for stations with incomplete months (particularly in Tier 3), determine whether gaps are systematic (sensor failure, seasonal shutdown) or random — this is prerequisite for imputation modelling.

4. **Multi-file stations in 2024**: audit which stations have `data-2.csv` or higher and verify the completeness calculation in `01_data_inventory.ipynb` correctly aggregates across all data files.

5. **Schema harmonisation**: design a unified intermediate schema (Site, Time, Direction, Volume, F1-F15, BinDuration_sec, AvgSpeed, Coverage_pct) that can accommodate all three tiers, enabling longitudinal analysis.

6. **Functional class QA**: cross-check `functional_class` values in the catalog against HPMS/FHWA definitions; flag any stations where `functional_class` is null (see null audit table).

7. **Completeness thresholding sensitivity**: the 80% threshold is hardcoded in the existing pipeline. Evaluate whether different thresholds (e.g., 70%, 90%) materially change which station-months are flagged as usable.
"""

    out = OUT_DIR / "inventory_summary.md"
    out.write_text(content)
    print(f"    Saved: {out}")


# ── Verify all outputs ─────────────────────────────────────────────────────────
def verify_outputs():
    print("\n[VERIFY] Checking all required outputs …")
    required = [
        "station_inventory_agent.py",
        "station_master_table.csv",
        "schema_audit_notes.txt",
        "fig_functional_class.png",
        "fig_urban_rural.png",
        "fig_data_source_overlap.png",
        "fig_completeness_distribution.png",
        "inventory_summary.md",
    ]
    all_ok = True
    for fname in required:
        fpath = OUT_DIR / fname
        exists = fpath.exists()
        size   = fpath.stat().st_size if exists else 0
        status = "OK" if exists and size > 0 else "MISSING or EMPTY"
        print(f"    [{status:25s}] {fname}  ({size:,} bytes)")
        if status != "OK":
            all_ok = False
    if all_ok:
        print("\n[VERIFY] All outputs present and non-empty. SUCCESS.")
    else:
        print("\n[VERIFY] WARNING: some outputs missing.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("GDOT Station Inventory Agent")
    print("=" * 60)

    catalog_df          = load_catalog()
    merged_comp, c24, c2223, c1722 = load_completeness()
    agg_comp            = aggregate_completeness(merged_comp)
    presence_df, xtab   = source_crosstab(catalog_df)
    null_audit          = metadata_null_audit(catalog_df)
    fig_functional_class(catalog_df)
    fig_urban_rural(catalog_df)
    schema_audit()
    id_check            = check_nonstandard_ids(catalog_df, presence_df)
    master_df           = build_master_table(catalog_df, agg_comp, presence_df)
    fig_data_source_overlap(presence_df, xtab)
    fig_completeness_distribution(merged_comp)
    write_summary(catalog_df, master_df, merged_comp, xtab, null_audit, id_check)
    verify_outputs()
    print("\nDone.")


if __name__ == "__main__":
    main()
