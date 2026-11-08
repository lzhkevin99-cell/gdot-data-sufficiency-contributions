"""
Bridges the EDA outage taxonomy to the paper's k* thresholds.
Produces fig_sufficiency_bands.png and sufficiency_summary.csv.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

OUT = Path(__file__).resolve().parent
ANOM = Path(__file__).resolve().parent.parent / "anomalies"

# ── load data ────────────────────────────────────────────────────────────────
df = pd.read_csv(ANOM / "station_month_trustworthiness.csv")

# approximate observed days (coverage_pct is % of expected intervals present)
df["approx_days"] = (df["coverage_pct"] / 100 * 30).round(0).astype(int).clip(upper=30)

# ── classify into three bands ─────────────────────────────────────────────────
# k* conservative bound = 18 (covers all observed outage types from GDoT paper)
# Current SOP threshold = 26 days

def classify(d):
    if d >= 26:
        return "Pass SOP\n(≥26 days)"
    elif d >= 18:
        return "Certifiable\n(18–25 days)"
    else:
        return "Below k*\n(<18 days)"

df["band"] = df["approx_days"].apply(classify)

band_order = ["Pass SOP\n(≥26 days)", "Certifiable\n(18–25 days)", "Below k*\n(<18 days)"]
counts = df["band"].value_counts().reindex(band_order, fill_value=0)

# save summary CSV
summary = pd.DataFrame({
    "band": band_order,
    "count": counts.values,
    "pct": (counts.values / len(df) * 100).round(1),
})
summary.to_csv(OUT / "sufficiency_summary.csv", index=False)
print("Saved: sufficiency_summary.csv")
print(summary.to_string(index=False))

# ── figure ───────────────────────────────────────────────────────────────────
NAVY  = (0x1E/255, 0x32/255, 0x58/255)
GOLD  = (0xC4/255, 0x98/255, 0x2A/255)
RED   = (0xC0/255, 0x30/255, 0x30/255)
LIGHT = (0xF0/255, 0xF3/255, 0xF8/255)

colors = [NAVY, GOLD, RED]
labels = [
    f"Pass SOP  (≥26 days)\n{counts.iloc[0]:,} station-months ({counts.iloc[0]/len(df)*100:.1f}%)",
    f"Certifiable (18–25 days)\n{counts.iloc[1]:,} station-months ({counts.iloc[1]/len(df)*100:.1f}%)",
    f"Below k*   (<18 days)\n{counts.iloc[2]:,} station-months ({counts.iloc[2]/len(df)*100:.1f}%)",
]

fig, ax = plt.subplots(figsize=(9, 3.2))
fig.patch.set_facecolor("white")
ax.set_facecolor(LIGHT)

bars = ax.barh(
    [2, 1, 0],
    counts.values,
    color=colors,
    height=0.55,
    edgecolor="white",
    linewidth=1.5,
)

# value labels inside bars
for bar, val, lbl in zip(bars, counts.values, labels):
    x = bar.get_width()
    ax.text(x / 2, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", ha="center",
            fontsize=13, fontweight="bold", color="white")

# y-axis band labels (plain text, outside bars)
band_labels = [
    "Below k*\n(<18 days)",
    "Certifiable\n(18–25 days)",
    "Pass SOP\n(≥26 days)",
]
ax.set_yticks([0, 1, 2])
ax.set_yticklabels(band_labels, fontsize=10)

# annotation: SOP gap callout
ax.annotate(
    "↑ 26-day SOP rejects\nthese certifiable months",
    xy=(counts.iloc[1], 1),
    xytext=(counts.iloc[1] + 200, 1.55),
    fontsize=8.5, color="#333355",
    arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.4),
    ha="left",
)

ax.set_xlabel("Number of station-months", fontsize=10)
ax.set_title(
    "Station-Month Sufficiency Bands\n"
    "Conservative k* = 18 days  |  Current SOP = 26 days",
    fontsize=11, fontweight="bold", color=tuple(c for c in NAVY), pad=10,
)
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#AAAAAA")
ax.tick_params(colors="#555555")
ax.xaxis.label.set_color("#555555")
ax.set_xlim(0, counts.max() * 1.25)

plt.tight_layout()
plt.savefig(OUT / "fig_sufficiency_bands.png", dpi=150, bbox_inches="tight",
            facecolor="white")
print(f"Saved: fig_sufficiency_bands.png")
plt.close()
