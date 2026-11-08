"""
Fix blank holiday and long-weekend effect figures.
Uses clean_hourly_2024_trusted.csv + all_events_2024.csv.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
HOURLY = BASE / "eda_output/features/clean_hourly_2024_trusted.csv"
EVENTS = BASE / "outputs/all_events_2024.csv"
OUT = BASE / "eda_output/trends"
CATALOG = BASE / "outputs/station_catalog.csv"

# ── load data ──────────────────────────────────────────────────────────────
print("Loading hourly data …")
hourly = pd.read_csv(HOURLY, parse_dates=["date"])
hourly["date"] = pd.to_datetime(hourly["date"])

print("Loading events …")
events = pd.read_csv(EVENTS, parse_dates=["start", "end"])
events["start"] = pd.to_datetime(events["start"])
events["end"] = pd.to_datetime(events["end"])
events["station_name"] = events["station_name"].astype(str)

# load FC lookup
catalog = pd.read_csv(CATALOG, usecols=["station_name", "functional_class"])
catalog["station_name"] = catalog["station_name"].astype(str)
FC_MAP = {
    "1: Interstate": "FC1 Interstate",
    "2: Freeways and Expressways": "FC2 Freeway",
    "3: Other Principal Arterial": "FC3 OPA",
    "4: Minor Arterial": "FC4 Arterial",
    "5: Major Collector": "FC5 Collector",
}

# ── aggregate hourly → daily ───────────────────────────────────────────────
print("Aggregating to daily …")
daily = (
    hourly.groupby(["station_id", "date"])["total_volume"]
    .sum()
    .reset_index()
    .rename(columns={"total_volume": "daily_volume", "station_id": "station_name"})
)
daily["station_name"] = daily["station_name"].astype(str)
daily["dow"] = daily["date"].dt.dayofweek
daily["month"] = daily["date"].dt.month
daily = daily.merge(catalog, on="station_name", how="left")
daily["fc"] = daily["functional_class"].map(FC_MAP).fillna("Other")

# ── build date-level event flag table ─────────────────────────────────────
def expand_events(events_df):
    rows = []
    for _, row in events_df.iterrows():
        d = row["start"].normalize()
        end = row["end"].normalize()
        while d <= end:
            rows.append({"station_name": row["station_name"], "date": d,
                         "flag": row["flag"], "description": row.get("description", "")})
            d += pd.Timedelta(days=1)
    return pd.DataFrame(rows)

print("Expanding event flags …")
event_days = expand_events(events)
event_days["date"] = pd.to_datetime(event_days["date"])

# ── FIGURE 1: Holiday Effect ───────────────────────────────────────────────
holidays = event_days[event_days["flag"] == "Holiday"].copy()
holidays["holiday_name"] = holidays["description"].str.strip()

# keep only the 6 main holidays
HOLIDAY_RENAME = {
    "Thanksgiving Day": "Thanksgiving",
    "Christmas Day": "Christmas",
}
holidays["holiday_name"] = holidays["holiday_name"].replace(HOLIDAY_RENAME)

MAIN_HOLIDAYS = [
    "New Year's Day", "Memorial Day", "Independence Day",
    "Labor Day", "Thanksgiving", "Christmas"
]
holidays = holidays[holidays["holiday_name"].isin(MAIN_HOLIDAYS)]

# build set of all flagged dates per station (any flag) for control exclusion
all_flagged = event_days[["station_name", "date"]].drop_duplicates()
all_flagged["is_flagged"] = True

# join daily with holiday labels
daily_hol = daily.merge(
    holidays[["station_name", "date", "holiday_name"]],
    on=["station_name", "date"], how="left"
)
daily_hol = daily_hol.merge(all_flagged, on=["station_name", "date"], how="left")
daily_hol["is_flagged"] = daily_hol["is_flagged"].fillna(False)

# compute holiday effect ratios
results = []
for (station, holiday), grp in daily_hol[daily_hol["holiday_name"].notna()].groupby(
    ["station_name", "holiday_name"]
):
    hol_vol = grp["daily_volume"].median()
    # control: same station, same DOW, not flagged, within 8 weeks
    hol_date = grp["date"].iloc[0]
    hol_dow = hol_date.dayofweek
    ctrl = daily_hol[
        (daily_hol["station_name"] == station)
        & (daily_hol["dow"] == hol_dow)
        & (~daily_hol["is_flagged"])
        & (abs((daily_hol["date"] - hol_date).dt.days) <= 56)
        & (daily_hol["daily_volume"] > 0)
    ]
    if len(ctrl) < 2:
        continue
    ctrl_median = ctrl["daily_volume"].median()
    if ctrl_median == 0:
        continue
    fc = grp["fc"].iloc[0]
    results.append({"holiday_name": holiday, "station_name": station,
                    "effect_ratio": hol_vol / ctrl_median, "fc": fc})

ratio_df = pd.DataFrame(results)
print(f"Holiday effect ratios computed: {len(ratio_df)} station-holiday pairs")

# plot
ORDER = ["New Year's Day", "Memorial Day", "Independence Day",
         "Labor Day", "Thanksgiving", "Christmas"]
FC_COLORS = {
    "FC1 Interstate": "#2196F3", "FC2 Freeway": "#9C27B0",
    "FC3 OPA": "#4CAF50", "FC4 Arterial": "#FF9800", "FC5 Collector": "#F44336",
    "Other": "#9E9E9E"
}

fig, ax = plt.subplots(figsize=(13, 6))
present = [h for h in ORDER if h in ratio_df["holiday_name"].values]
x_pos = np.arange(len(present))
width = 0.13
fcs = [fc for fc in FC_COLORS if fc in ratio_df["fc"].values]

for i, fc in enumerate(fcs):
    sub = ratio_df[ratio_df["fc"] == fc]
    vals = [sub[sub["holiday_name"] == h]["effect_ratio"].dropna().values for h in present]
    medians = [np.median(v) if len(v) else np.nan for v in vals]
    offset = (i - len(fcs) / 2 + 0.5) * width
    ax.bar(x_pos + offset, medians, width=width * 0.85,
           color=FC_COLORS[fc], alpha=0.85, label=fc)
    for xi, med in zip(x_pos + offset, medians):
        if not np.isnan(med):
            ax.text(xi, med + 0.01, f"{med:.2f}", ha="center", va="bottom",
                    fontsize=6.5, fontweight="bold")

ax.axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="No effect (ratio=1)")
ax.set_xticks(x_pos)
ax.set_xticklabels(present, fontsize=11)
ax.set_ylabel("Volume Ratio vs. Control Days", fontsize=12)
ax.set_title("Holiday Effect on Daily Traffic Volume — 2024\n(ratio < 1 = volume drop)", fontsize=13, fontweight="bold")
ax.legend(fontsize=9, ncol=3, loc="lower right")
ax.set_ylim(0, 1.3)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
fig.savefig(OUT / "fig_holiday_effect.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved fig_holiday_effect.png")

# ── FIGURE 2: Long Weekend Effects ────────────────────────────────────────
LONG_WEEKENDS = {
    "Memorial Day\n(May 25)": pd.Timestamp("2024-05-25"),
    "Independence Day\n(Jul 4)": pd.Timestamp("2024-07-04"),
    "Labor Day\n(Sep 2)": pd.Timestamp("2024-09-02"),
}
DAY_LABELS = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue"]
DAY_OFFSETS = [-1, 0, 1, 2, 3, 4]  # days relative to holiday Monday/Friday

LW_COLORS = {"Memorial Day\n(May 25)": "#E53935",
             "Independence Day\n(Jul 4)": "#1565C0",
             "Labor Day\n(Sep 2)": "#2E7D32"}

fig, ax = plt.subplots(figsize=(11, 6))

for lw_name, anchor in LONG_WEEKENDS.items():
    # for Memorial/Labor Day anchor is Monday; IndependenceDay anchor is Thursday
    ratios_by_offset = []
    for offset in DAY_OFFSETS:
        target_date = anchor + pd.Timedelta(days=offset)
        target_dow = target_date.dayofweek
        # long weekend volume for this day
        lw_vol = daily[daily["date"] == target_date]["daily_volume"]
        # baseline: same DOW, same stations, 4 non-holiday weekends in same month ±6 weeks
        ctrl_dates = [target_date + pd.Timedelta(weeks=w) for w in [-4, -2, 2, 4]]
        ctrl_vol = daily[daily["date"].isin(ctrl_dates)]["daily_volume"]
        if len(lw_vol) == 0 or len(ctrl_vol) == 0:
            ratios_by_offset.append(np.nan)
            continue
        ratio = lw_vol.median() / ctrl_vol.median() if ctrl_vol.median() > 0 else np.nan
        ratios_by_offset.append(ratio)
    ax.plot(DAY_LABELS, ratios_by_offset, marker="o", linewidth=2.2,
            label=lw_name, color=LW_COLORS[lw_name])
    for xi, ratio in zip(range(len(DAY_LABELS)), ratios_by_offset):
        if not np.isnan(ratio):
            ax.text(xi, ratio + 0.015, f"{ratio:.2f}", ha="center", fontsize=8.5)

ax.axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="Baseline (ratio=1)")
ax.axvspan(1, 3, alpha=0.07, color="gray", label="Core long weekend (Fri–Sun)")
ax.set_ylabel("Median Daily Volume Ratio vs. Baseline", fontsize=12)
ax.set_title("Long Weekend Traffic Effect — 2024\n(relative to same day-of-week baseline ±2–4 weeks)", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.set_ylim(0.5, 1.4)
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
fig.savefig(OUT / "fig_long_weekend_effects.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved fig_long_weekend_effects.png")
print("Done.")
