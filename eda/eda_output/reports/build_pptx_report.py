"""
Build GDOT EDA Final Report as a PowerPoint (.pptx) file.
15 slides — storytelling-first revision.
Story arc: Setup -> Trust -> Understanding -> Readiness
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
OUT  = BASE / "eda_output/reports/gdot_eda_final_report.pptx"

INV  = BASE / "eda_output/inventory"
MISS = BASE / "eda_output/missingness"
PROF = BASE / "eda_output/profiles"
TREN = BASE / "eda_output/trends"
CORR = BASE / "eda_output/corridors"
ANOM = BASE / "eda_output/anomalies"
FEAT = BASE / "eda_output/features"
INV2 = BASE / "outputs/figures/01_inventory"

NAVY  = RGBColor(0x17, 0x36, 0x5D)
STEEL = RGBColor(0x46, 0x82, 0xB4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xDC, 0xE6, 0xF2)
DARK  = RGBColor(0x1E, 0x1E, 0x1E)
GRAY  = RGBColor(0x90, 0x90, 0x90)
RED   = RGBColor(0xB4, 0x1E, 0x1E)
GREEN = RGBColor(0x1E, 0x82, 0x3C)
GOLD  = RGBColor(0xFF, 0xC8, 0x00)
LGRAY = RGBColor(0xE8, 0xE8, 0xE8)

SW = Inches(13.33)
SH = Inches(7.5)

prs = Presentation()
prs.slide_width  = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]

TOTAL = 15   # total slide count for footer

# ── helpers ───────────────────────────────────────────────────────────────

def add_slide():
    return prs.slides.add_slide(BLANK)

def rect(slide, l, t, w, h, fill=None, line=None):
    sh = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.line.fill.background()
    if fill:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    else:
        sh.fill.background()
    if line:
        sh.line.color.rgb = line; sh.line.width = Pt(0.5)
    else:
        sh.line.fill.background()
    return sh

def txbox(slide, l, t, w, h, text, size=11, bold=False, color=DARK,
          align=PP_ALIGN.LEFT, wrap=True, italic=False):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size = Pt(size); run.font.bold = bold
    run.font.italic = italic; run.font.color.rgb = color
    return tb

def header(slide, title, color=NAVY):
    rect(slide, 0, 0, 13.33, 0.75, fill=color)
    rect(slide, 0, 0, 0.18, 0.75, fill=GOLD)
    txbox(slide, 0.28, 0.1, 12.8, 0.55, title, size=20, bold=True, color=WHITE)

def footer(slide, page_num):
    rect(slide, 0, 7.17, 13.33, 0.33, fill=NAVY)
    txbox(slide, 0.2, 7.2, 9, 0.28,
          "GDOT Traffic Dataset EDA  |  2017-2024  |  Georgia DOT",
          size=7, color=LIGHT)
    txbox(slide, 11.5, 7.2, 1.7, 0.28,
          f"Slide {page_num} / {TOTAL}", size=7, color=LIGHT, align=PP_ALIGN.RIGHT)

def place_img(slide, path, l, t, w, h):
    p = Path(path)
    if p.exists():
        slide.shapes.add_picture(str(p), Inches(l), Inches(t), Inches(w), Inches(h))
    else:
        bx = rect(slide, l, t, w, h, line=GRAY)
        bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5)
        txbox(slide, l, t + h/2 - 0.1, w, 0.25, p.name, size=7, color=GRAY,
              align=PP_ALIGN.CENTER)

def section_label(slide, l, t, w, text, color=STEEL):
    rect(slide, l, t, w, 0.22, fill=color)
    txbox(slide, l + 0.05, t + 0.02, w - 0.1, 0.18, text, size=8, bold=True, color=WHITE)

def kv_table(slide, l, t, w, rows, col1_frac=0.5, fontsize=9):
    col1 = w * col1_frac; col2 = w * (1 - col1_frac); row_h = 0.22
    for i, (k, v) in enumerate(rows):
        fill_c = LIGHT if i % 2 == 0 else WHITE
        rect(slide, l, t, col1, row_h, fill=fill_c)
        rect(slide, l + col1, t, col2, row_h, fill=fill_c)
        txbox(slide, l + 0.05, t + 0.02, col1 - 0.05, row_h - 0.02,
              k, size=fontsize, bold=True, color=DARK)
        txbox(slide, l + col1 + 0.05, t + 0.02, col2 - 0.1, row_h - 0.02,
              str(v), size=fontsize, color=DARK)
        t += row_h
    return t

def bullets(slide, l, t, w, items, fontsize=9.5, line_h=0.24):
    for item in items:
        txbox(slide, l, t, 0.15, line_h, "-", size=fontsize, bold=True, color=NAVY)
        tb = slide.shapes.add_textbox(Inches(l + 0.15), Inches(t),
                                       Inches(w - 0.15), Inches(line_h * 2.5))
        tb.text_frame.word_wrap = True
        p = tb.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
        run = p.add_run(); run.text = item
        run.font.size = Pt(fontsize); run.font.color.rgb = DARK
        t += line_h
    return t

def implication(slide, text):
    """Gold-accented navy callout bar pinned to the bottom of body area."""
    rect(slide, 0.2, 6.72, 12.93, 0.38, fill=NAVY)
    rect(slide, 0.2, 6.72, 0.12, 0.38, fill=GOLD)
    txbox(slide, 0.42, 6.76, 2.4, 0.3, "Modeling Implication:",
          size=8.5, bold=True, color=GOLD)
    txbox(slide, 2.85, 6.76, 10.2, 0.3, text, size=8.5, color=WHITE)

def phase_box(slide, l, t, w, h, letter, title, detail, color=NAVY, deferred=False):
    c = LGRAY if deferred else color
    tc = GRAY if deferred else WHITE
    rect(slide, l, t, w, h, fill=c)
    rect(slide, l, t, w, 0.06, fill=GOLD if not deferred else GRAY)
    txbox(slide, l, t + 0.12, w, 0.55, letter, size=28, bold=True, color=tc,
          align=PP_ALIGN.CENTER)
    txbox(slide, l, t + 0.68, w, 0.35, title, size=11, bold=True, color=tc,
          align=PP_ALIGN.CENTER)
    txbox(slide, l + 0.1, t + 1.08, w - 0.2, h - 1.15, detail, size=8.5,
          color=GRAY if deferred else LIGHT, wrap=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
rect(sl, 0, 0, 13.33, 7.5, fill=NAVY)
rect(sl, 0, 0, 0.22, 7.5, fill=GOLD)
rect(sl, 0, 2.9, 13.33, 0.06, fill=STEEL)
txbox(sl, 0.4, 1.8, 12, 0.8, "GDOT Traffic Dataset",
      size=40, bold=True, color=WHITE)
txbox(sl, 0.4, 2.65, 12, 0.6, "Exploratory Data Analysis",
      size=28, bold=True, color=LIGHT)
txbox(sl, 0.4, 3.25, 12, 0.4,
      "2017 - 2024  |  Georgia Department of Transportation",
      size=16, color=LIGHT)
txbox(sl, 0.4, 3.85, 12, 0.35,
      "286 Stations  |  3 Data Tiers  |  7 Analysis Tracks  |  EDA Phase Complete",
      size=13, color=STEEL)
footer(sl, 1)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — The Question We're Answering  [NEW]
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
rect(sl, 0, 0, 13.33, 7.5, fill=LIGHT)
rect(sl, 0, 0, 13.33, 0.75, fill=NAVY)
rect(sl, 0, 0, 0.18, 0.75, fill=GOLD)
txbox(sl, 0.28, 0.1, 12.8, 0.55, "The Question We're Answering",
      size=20, bold=True, color=WHITE)
footer(sl, 2)

# Central question box
rect(sl, 1.2, 1.1, 10.93, 1.4, fill=NAVY)
rect(sl, 1.2, 1.1, 0.18, 1.4, fill=GOLD)
txbox(sl, 1.55, 1.25, 10.5, 1.1,
      "Can we use GDOT's 8-year traffic sensor dataset to reliably estimate "
      "Annual Average Daily Traffic (AADT) across Georgia?",
      size=18, bold=True, color=WHITE, wrap=True)

# Three sub-questions
sub_qs = [
    ("1", "Is the data complete and trustworthy enough to use?",
     "286 stations, 2017-2024. How much is missing? Is what remains reliable?"),
    ("2", "What does normal traffic behavior look like?",
     "Daily volumes, peak hours, weekday/weekend patterns, seasonal trends."),
    ("3", "What do we need to build the AADT model?",
     "Clean datasets, engineered features, gap-filling strategy, reference stations."),
]
for i, (num, q, sub) in enumerate(sub_qs):
    x = 0.5 + i * 4.28
    rect(sl, x, 2.85, 4.05, 3.7, fill=WHITE)
    rect(sl, x, 2.85, 4.05, 0.06, fill=STEEL)
    txbox(sl, x + 0.1, 2.97, 0.45, 0.5, num, size=22, bold=True, color=STEEL)
    txbox(sl, x + 0.55, 2.97, 3.4, 0.6, q, size=11, bold=True, color=NAVY, wrap=True)
    txbox(sl, x + 0.1, 3.75, 3.85, 2.5, sub, size=10, color=GRAY, wrap=True)

txbox(sl, 0.5, 6.75, 12.33, 0.3,
      "This presentation answers all three questions -- starting with the data, "
      "ending with what is ready for modeling.",
      size=9, italic=True, color=GRAY, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — EDA Workflow: How We Got Here  [NEW]
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
rect(sl, 0, 0, 13.33, 7.5, fill=NAVY)
rect(sl, 0, 0, 13.33, 0.75, fill=RGBColor(0x0D, 0x20, 0x40))
rect(sl, 0, 0, 0.18, 0.75, fill=GOLD)
txbox(sl, 0.28, 0.1, 12.8, 0.55, "EDA Workflow: How We Got Here",
      size=20, bold=True, color=WHITE)
footer(sl, 3)

steps = [
    ("Data\nInventory",    "286 stations\nacross 3 tiers"),
    ("Quality\nAudit",     "8.4% missing\nstructured gaps"),
    ("Traffic\nBehavior",  "Predictable peaks\n7 AM and 5 PM"),
    ("Temporal\nTrends",   "COVID drop\nrecovered by 2022"),
    ("Corridor\nAnalysis", "27 reference\nstations found"),
    ("Anomaly\nDetection", "90.5% of anomalies\nexplained"),
    ("Modeling\nReadiness","818K records\nready for AADT"),
]
box_w = 1.58; gap = 0.22; start_x = 0.4; box_t = 1.5; box_h = 3.8

for i, (name, result) in enumerate(steps):
    x = start_x + i * (box_w + gap)
    is_last = (i == len(steps) - 1)
    box_color = GREEN if is_last else STEEL
    rect(sl, x, box_t, box_w, box_h, fill=box_color)
    rect(sl, x, box_t, box_w, 0.08, fill=GOLD)
    # step number circle
    rect(sl, x + box_w/2 - 0.18, box_t + 0.15, 0.36, 0.36, fill=NAVY)
    txbox(sl, x + box_w/2 - 0.18, box_t + 0.15, 0.36, 0.36, str(i + 1),
          size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # step name
    txbox(sl, x + 0.05, box_t + 0.62, box_w - 0.1, 0.8, name,
          size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # result line
    rect(sl, x + 0.1, box_t + 1.55, box_w - 0.2, 0.03, fill=GOLD)
    txbox(sl, x + 0.05, box_t + 1.7, box_w - 0.1, 1.9, result,
          size=9, color=LIGHT, align=PP_ALIGN.CENTER, wrap=True)
    # arrow to next
    if not is_last:
        ax = x + box_w + 0.03
        txbox(sl, ax, box_t + box_h/2 - 0.15, gap - 0.03, 0.35,
              ">", size=14, bold=True, color=GOLD, align=PP_ALIGN.CENTER)

txbox(sl, 0.4, 5.6, 12.53, 0.4,
      "Each step built on the last. The goal throughout: understand the data well enough "
      "to justify every modeling decision that follows.",
      size=10, italic=True, color=LIGHT, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — The Dataset in 5 Numbers  (merged inventory + completeness)
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "The Dataset in 5 Numbers", STEEL)
footer(sl, 4)

# Five stat boxes across the top
stat_data = [
    ("286",   "Stations\nAnalyzed", NAVY),
    ("8",     "Years of\nData",     STEEL),
    ("91.6%", "Station-Months\nComplete", GREEN),
    ("243",   "Trusted\nStations",  NAVY),
    ("818K",  "Clean Hourly\nRecords (2024)", STEEL),
]
box_w = 2.35; gap_x = 0.17; start_x = 0.27
for i, (val, lbl, col) in enumerate(stat_data):
    x = start_x + i * (box_w + gap_x)
    rect(sl, x, 0.85, box_w, 1.55, fill=col)
    rect(sl, x, 0.85, box_w, 0.07, fill=GOLD)
    txbox(sl, x, 1.0, box_w, 0.75, val, size=32, bold=True, color=WHITE,
          align=PP_ALIGN.CENTER)
    txbox(sl, x, 1.75, box_w, 0.55, lbl, size=9, color=LIGHT,
          align=PP_ALIGN.CENTER, wrap=True)

# Bottom: figures + key bullets
place_img(sl, INV / "fig_functional_class.png",           0.2,  2.6, 3.8, 2.6)
place_img(sl, INV / "fig_urban_rural.png",                4.1,  2.6, 3.8, 2.6)
place_img(sl, INV2 / "03_completeness_heatmap_2024.png",  8.05, 2.6, 5.1, 2.6)

txbox(sl, 0.2, 5.3, 7.65, 0.22,
      "Fleet: 42% Interstate (FC1). ~70% urban. 225 stations in all 3 tiers. "
      "Active count: 258 (2018) declining to 233 (2024).",
      size=8, italic=True, color=GRAY)
txbox(sl, 8.05, 5.3, 5.1, 0.22,
      "Completeness heatmap: each row = one station, each column = one month. "
      "White = missing. Most of the heatmap is dark.",
      size=8, italic=True, color=GRAY)

txbox(sl, 0.2, 5.65, 12.93, 0.28,
      "Tier complete-month rates: 93.3% (Tier 2)  |  94.9% (Tier 1)  |  "
      "98.8% (Tier 3)  |  Mean per station: 72.9 complete months",
      size=9, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Why Three Tiers Make Cross-Period Analysis Hard  (simplified arch)
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Why Three Tiers Make Cross-Period Analysis Hard", STEEL)
footer(sl, 5)

place_img(sl, INV2 / "01_station_catalog_profiling.png", 0.2, 0.85, 6.8, 5.9)

# Tier table
section_label(sl, 7.3, 0.85, 5.8, "Three Tiers -- Three Different Schemas")
kv_table(sl, 7.3, 1.1, 5.8, [
    ("Tier 1 (2024)",         "5-min, directional, speed + weight bins. 12-digit COSIT filename."),
    ("Tier 2 (2022-23)",      "5-min, lane-level (not directional), no speed/weight data."),
    ("Tier 3 (2017-22)",      "Hourly, directional, average speed + QC flags only."),
    ("All-3-tier stations",   "225  (78.7% of the fleet -- best for longitudinal analysis)"),
    ("Single-tier stations",  "34  (limited history -- treat with caution in trend analysis)"),
], col1_frac=0.35, fontsize=9.5)

section_label(sl, 7.3, 3.0, 5.8, "Why Joining Across Tiers Is Difficult")
bullets(sl, 7.3, 3.25, 5.7, [
    "ID format changes: Tier 1 uses 12-digit COSIT in filename; "
    "Tiers 2-3 use XXX-XXXX station name. Cross-tier joins require explicit lookup.",
    "Resolution changes: Tier 3 is hourly; Tiers 1-2 are 5-minute. "
    "Direct comparison requires resampling.",
    "Stratification changes: Tier 2 is lane-level, not directional -- "
    "cannot compare NB/SB splits between 2022-23 and 2024.",
    "Cross-tier joining is handled in the pipeline. These issues are documented "
    "but resolved for the analysis presented here.",
], fontsize=9.5, line_h=0.27)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Missingness Has a Pattern -- Not Random
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Missingness Has a Pattern -- and That Pattern Tells Us Something")
footer(sl, 6)

place_img(sl, MISS / "fig_missingness_by_station_heatmap.png", 0.2, 0.85, 7.8, 3.0)
place_img(sl, MISS / "fig_missingness_by_year.png",             0.2, 3.95, 7.8, 2.65)

section_label(sl, 8.3, 0.85, 4.8, "Fleet-Wide Picture")
bullets(sl, 8.3, 1.1, 4.8, [
    "8.4% overall missingness -- but not evenly distributed",
    "73.4% of stations are 'always-on' (>=90% complete months)",
    "Only 1.8% are chronically sparse (<40% complete months)",
    "226 outage runs; 73 runs exceed 6 months (max 60 months)",
], fontsize=9.5, line_h=0.28)

section_label(sl, 8.3, 2.35, 4.8, "The Year-over-Year Pattern")
bullets(sl, 8.3, 2.6, 4.8, [
    "2017: 13.6% -- incomplete initial deployment",
    "2022-23: 12% spike -- pipeline transition to 5-min system",
    "2024: 7.8% -- partial recovery",
    "This is NOT random. Gaps cluster around operational events.",
], fontsize=9.5, line_h=0.28)

section_label(sl, 8.3, 4.05, 4.8, "What This Means")
bullets(sl, 8.3, 4.3, 4.8, [
    "Long outage runs (>6 months) = sensor replacement cycles, not accidents",
    "2022-23 spike: flag these months in longitudinal models",
], fontsize=9.5, line_h=0.28)

implication(sl, "Missingness is structured and operationally driven. "
    "Simple mean-fill imputation will not work -- "
    "we need behavioral-neighbor-based gap filling.")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Interstates Miss More -- Likely Methodology, Not Sensors
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Interstates Miss More -- Likely a Methodology Issue, Not a Sensor Issue")
footer(sl, 7)

place_img(sl, MISS / "fig_missingness_by_fc.png",        0.2,  0.85, 4.3, 5.8)
place_img(sl, MISS / "fig_run_length_distribution.png",  4.65, 0.85, 4.0, 2.85)
place_img(sl, MISS / "fig_hourly_bias_sample.png",       4.65, 3.8,  4.0, 2.8)

section_label(sl, 8.85, 0.85, 4.25, "Key Patterns")
bullets(sl, 8.85, 1.1, 4.25, [
    "FC1 Interstate: 13.5% missingness -- highest class",
    "FC2 Freeways: 14.6% -- even higher",
    "FC3-5 Arterials/Collectors: only 3.2% to 5.4%",
    "Counterintuitive: shouldn't important roads have better coverage?",
    "Likely explanation: multi-lane sensors generate more expected "
    "bins per interval, making the 80% threshold harder to meet",
    "Run lengths: 52% single-month (maintenance); "
    "32% exceed 6 months (sensor replacement)",
    "Hour bias: most missing at 6 AM; most reliable at 4 PM",
], fontsize=9.5, line_h=0.26)

implication(sl, "Interstate/freeway missingness may be a measurement artifact, "
    "not a data quality failure -- validate before excluding these stations from models.")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — VERDICT: 84.9% of Stations Pass Quality Checks
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "VERDICT: 84.9% of Stations Pass All Quality Checks", RED)
footer(sl, 8)

place_img(sl, ANOM / "fig_anomaly_timeline.png",        0.2, 0.85, 7.8, 3.1)
place_img(sl, ANOM / "fig_trust_tier_distribution.png", 0.2, 4.05, 7.8, 2.55)

# Verdict headline
rect(sl, 8.3, 0.85, 4.8, 1.45, fill=NAVY)
rect(sl, 8.3, 0.85, 0.15, 1.45, fill=GREEN)
txbox(sl, 8.55, 0.92, 4.45, 0.55, "VERDICT:", size=22, bold=True, color=GREEN)
txbox(sl, 8.55, 1.45, 4.45, 0.35, "The data is trustworthy.", size=13, bold=True, color=WHITE)
txbox(sl, 8.55, 1.82, 4.45, 0.4,
      "84.9% of stations pass all quality checks.\n"
      "90.5% of detected anomalies are explained by\n"
      "known events in the GDOT event database.",
      size=8.5, color=LIGHT, italic=True, wrap=True)

# Anomaly callout
rect(sl, 8.3, 2.45, 4.8, 0.55, fill=STEEL)
txbox(sl, 8.4, 2.5, 4.6, 0.2, "Anomaly Detection (58 stations, 2024):", size=8, bold=True, color=WHITE)
txbox(sl, 8.4, 2.7, 4.6, 0.25,
      "391 anomaly-days found.  354 explained (90.5%).  37 unexplained (9.5%).",
      size=8.5, color=WHITE)

# Consolidated trust table (3-column)
section_label(sl, 8.3, 3.1, 4.8, "Station Trust Tiers (286 Stations)")
# header row
rect(sl, 8.3, 3.32, 1.55, 0.22, fill=NAVY)
rect(sl, 9.85, 3.32, 1.62, 0.22, fill=NAVY)
rect(sl, 11.47, 3.32, 1.63, 0.22, fill=NAVY)
txbox(sl, 8.35, 3.34, 1.5, 0.18, "Tier", size=8, bold=True, color=WHITE)
txbox(sl, 9.9, 3.34, 1.57, 0.18, "Station-Months", size=8, bold=True, color=WHITE)
txbox(sl, 11.52, 3.34, 1.58, 0.18, "Stations", size=8, bold=True, color=WHITE)
# data rows
trust_rows = [
    ("TRUSTED",  "19,963  (96.9%)", "243  (84.9%)", LIGHT),
    ("CAUTION",  "233  (1.1%)",     "36  (12.6%)",  WHITE),
    ("EXCLUDED", "404  (2.0%)",     "7  (2.5%)",    LIGHT),
]
for i, (tier, sm, st, bg) in enumerate(trust_rows):
    y = 3.54 + i * 0.22
    rect(sl, 8.3,   y, 1.55, 0.22, fill=bg)
    rect(sl, 9.85,  y, 1.62, 0.22, fill=bg)
    rect(sl, 11.47, y, 1.63, 0.22, fill=bg)
    c = GREEN if tier == "TRUSTED" else (RED if tier == "EXCLUDED" else DARK)
    txbox(sl, 8.35,  y + 0.02, 1.5,  0.18, tier, size=8.5, bold=True, color=c)
    txbox(sl, 9.9,   y + 0.02, 1.57, 0.18, sm,   size=8.5, color=DARK)
    txbox(sl, 11.52, y + 0.02, 1.58, 0.18, st,   size=8.5, color=DARK)

# Callout: what this means for modeling
rect(sl, 8.3, 4.25, 4.8, 0.85, fill=LIGHT)
rect(sl, 8.3, 4.25, 0.1, 0.85, fill=GREEN)
txbox(sl, 8.5, 4.3, 4.5, 0.3, "What this means:", size=9, bold=True, color=NAVY)
txbox(sl, 8.5, 4.6, 4.5, 0.45,
      "243 TRUSTED stations form the primary modeling population. "
      "36 CAUTION stations can be used in sensitivity tests. "
      "7 EXCLUDED need manual investigation.",
      size=8.5, color=DARK, wrap=True)

txbox(sl, 8.3, 5.2, 4.8, 0.25,
      "Note: trust assessment for 228 of 286 stations uses coverage proxy, "
      "not direct anomaly detection. Extending raw-data checks to the full fleet "
      "is a recommended next step.",
      size=7.5, italic=True, color=GRAY, wrap=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Traffic Is Predictable: Same Peaks, Every Day, Every Season
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Traffic Is Predictable: Same Peaks, Every Day, Every Season")
footer(sl, 9)

place_img(sl, PROF / "fig_hourly_profile_by_fc.png",  0.2,  0.85, 5.4, 5.8)
place_img(sl, PROF / "fig_dow_profile_by_fc.png",     5.75, 0.85, 3.8, 2.8)
place_img(sl, PROF / "fig_weekday_weekend_ratio.png", 5.75, 3.75, 3.8, 2.85)

section_label(sl, 9.75, 0.85, 3.35, "Volume Summary (100 stations, 2024)")
kv_table(sl, 9.75, 1.1, 3.35, [
    ("Median daily volume",     "22,830 veh/day"),
    ("Mean daily volume",       "45,223 veh/day"),
    ("FC2 Freeways (median)",   "~110,000 veh/day"),
    ("FC1 Interstate (median)", "~52,000 veh/day"),
    ("FC3 OPA (median)",        "~19,000 veh/day"),
    ("W/WE ratio (fleet avg)",  "1.25 -- weekday-heavy"),
    ("AM peak hour",            "07:00  (stable all seasons)"),
    ("PM peak hour",            "17:00  (stable all seasons)"),
], col1_frac=0.56, fontsize=9)

txbox(sl, 9.75, 3.0, 3.35, 0.65,
      "Interstates: W/WE ratio 1.08 -- nearly uniform 7-day use "
      "(freight + commuter mix). Arterials/Collectors: 1.35-1.44 -- "
      "strongly commuter-oriented.",
      size=8, italic=True, color=GRAY, wrap=True)

implication(sl, "Stable AM/PM peaks (7:00 and 17:00) are consistent across all "
    "functional classes and all four seasons -- "
    "reliable fixed features for AADT models. No time-varying peak adjustment needed.")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — COVID Dropped Traffic 8.6%. It Came Back by 2022.
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "COVID Dropped Traffic 8.6%. It Came Back by 2022.")
footer(sl, 10)

place_img(sl, TREN / "fig_aadt_trend_2017_2024.png",            0.2, 0.85, 7.5, 2.85)
place_img(sl, TREN / "fig_seasonal_decomposition_examples.png", 0.2, 3.8,  7.5, 2.8)

section_label(sl, 8.0, 0.85, 5.1, "AADT Proxy Trends (30-station sample, 2018-2023)")
bullets(sl, 8.0, 1.1, 5.1, [
    "COVID-19: median volume dropped ~8.6% from 2019 to 2020 across all FC",
    "Recovery: near-2019 levels restored by 2021-2022 for most stations",
    "Freeways recovered fastest; major collectors were slowest",
    "AADT proxy = June mean daily volume -- least seasonally biased "
    "month; avoids requirement for a full calendar year of data",
], fontsize=9.5, line_h=0.28)

section_label(sl, 8.0, 2.5, 5.1, "Seasonality (2023 baseline)")
bullets(sl, 8.0, 2.75, 5.1, [
    "Peak month: October  (Seasonal Index = 1.036)",
    "Trough month: January  (SI = 0.928) -- +/-10% annual amplitude",
    "Rural FC4-5 stations show stronger seasonality than Interstate",
    "Peak hours (7 AM / 5 PM) are stable across all 4 seasons",
], fontsize=9.5, line_h=0.28)

implication(sl, "COVID drop is real but fully recovered by 2022. "
    "Use 2022-2024 as the primary training window. "
    "Stations with seasonal amplitude >0.4 need June-proxy correction.")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Holidays Reduce Traffic -- We Now Have the Correction Factors
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Holidays Reduce Traffic -- We Now Have the Correction Factors")
footer(sl, 11)

place_img(sl, TREN / "fig_holiday_effect.png",       0.2, 0.85, 7.8, 3.0)
place_img(sl, TREN / "fig_long_weekend_effects.png", 0.2, 3.95, 7.8, 2.72)

section_label(sl, 8.3, 0.85, 4.8, "What the Charts Show")
bullets(sl, 8.3, 1.1, 4.8, [
    "All major holidays show reduced traffic (ratio < 1.0)",
    "Independence Day: largest single-day drop -- down ~23% on average",
    "Thanksgiving and Christmas: sustained reductions of 25-40%",
    "Memorial Day and Labor Day: milder (10-20%) -- travel partially offsets commuter drop",
    "Interstates hold up best on holidays (freight + through traffic continues)",
    "Arterials and collectors drop most (commuter-dependent traffic stops)",
], fontsize=9.5, line_h=0.27)

section_label(sl, 8.3, 2.85, 4.8, "Long Weekend Pattern")
bullets(sl, 8.3, 3.1, 4.8, [
    "Traffic drops sharply the Friday before a holiday Monday",
    "Recovery is gradual -- volumes return to normal by Tuesday",
    "Independence Day (mid-week): concentrated single-day drop only",
], fontsize=9.5, line_h=0.27)

section_label(sl, 8.3, 4.1, 4.8, "Modeling Implication")
txbox(sl, 8.3, 4.35, 4.8, 1.1,
      "Holiday days in the training data will pull estimated AADT downward "
      "if included without adjustment. These effect ratios are the "
      "correction factors -- apply them when computing AADT from "
      "daily traffic totals that include holiday dates.",
      size=9.5, color=NAVY, wrap=True)

txbox(sl, 0.2, 6.75, 7.8, 0.25,
      "Ratios computed from 99-station 2024 hourly dataset vs. same-day-of-week control windows.",
      size=7.5, italic=True, color=GRAY)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 12 — Stations Move Together -- 27 Are Ready to Fill In for Others
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Stations Move Together -- 27 Are Ready to Fill In for Others", GREEN)
footer(sl, 12)

place_img(sl, CORR / "fig_correlation_heatmap.png",     0.2, 0.85, 5.5, 5.8)
place_img(sl, CORR / "fig_geographic_clusters_map.png", 5.9, 0.85, 4.2, 5.8)

section_label(sl, 10.3, 0.85, 2.8, "Pairwise Correlation (top 80 stations)")
kv_table(sl, 10.3, 1.1, 2.8, [
    ("Valid pairs",        "2,848  (>=180 overlapping days)"),
    ("Mean Pearson r",     "0.573  (median 0.636)"),
    ("High-corr (r>0.85)","411 pairs  (14.4% of all pairs)"),
], col1_frac=0.5, fontsize=9)

section_label(sl, 10.3, 1.95, 2.8, "Clusters and Reference Stations")
bullets(sl, 10.3, 2.2, 2.8, [
    "7 multi-station corridor clusters identified",
    "211 behavioral neighbor pairs (r>0.7, dist<50km)",
    "27 reference stations pass all 5 quality criteria",
    "Top: 089-3323 (DeKalb, Interstate, 10 neighbors)",
    "Note: analysis covers top 80 only -- ~150 more eligible stations not yet assessed",
], fontsize=9, line_h=0.26)

implication(sl, "27 reference stations are our gap-filling donors. "
    "When a station has missing data, we borrow from its behavioral neighbor -- "
    "not a generic fleet average. This is more accurate and corridor-aware.")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 13 — What We Built: 818K Records, 286 Features, Ready for AADT
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "What We Built: 818K Records, 286 Features, Ready for AADT", GREEN)
footer(sl, 13)

place_img(sl, FEAT / "fig_aggregation_comparison.png", 0.2, 0.85, 6.5, 5.97)

section_label(sl, 6.9, 0.85, 6.2, "Clean Hourly 2024 Dataset")
kv_table(sl, 6.9, 1.1, 6.2, [
    ("Hourly records",           "818,645"),
    ("Trusted stations covered", "99 of 207 eligible"),
    ("Temporal span",            "Full calendar year 2024"),
    ("Mean hourly coverage",     "100%  (min threshold: 50%)"),
    ("Imputed hours",            "1.7%  (flagged, not removed)"),
    ("Median hourly volume",     "580 veh/hr  (max 17,822)"),
], col1_frac=0.5, fontsize=9.5)

section_label(sl, 6.9, 2.65, 6.2, "Station Feature Table")
kv_table(sl, 6.9, 2.9, 6.2, [
    ("Dimensions",             "286 stations  x  27 features"),
    ("AADT proxy",             "median_daily x 365  (June-reference-free)"),
    ("Seasonal amplitude",     "per station from 2023 data"),
    ("Recommended resolution", "Hourly -- preserves AM/PM peaks, reduces noise"),
], col1_frac=0.5, fontsize=9.5)

section_label(sl, 6.9, 3.95, 6.2, "Outputs Ready for Modeling")
kv_table(sl, 6.9, 4.18, 6.2, [
    ("station_feature_table.csv",        "286 stations x 27 modeling features"),
    ("clean_hourly_2024_trusted.csv",    "818K hourly records, 99 stations, 26 cols"),
    ("reference_station_candidates.csv", "27 top gap-filling donor stations"),
    ("trusted_station_list.csv",         "243 HIGH-trust stations"),
    ("holiday_effect ratios",            "6 major holidays, by functional class"),
], col1_frac=0.52, fontsize=9)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Modeling Plan: Four Phases  [NEW]
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "Modeling Plan: Four Phases", GREEN)
footer(sl, 14)

txbox(sl, 0.3, 0.85, 12.73, 0.35,
      "The EDA produced four distinct modeling-ready outputs. Each phase builds on the last.",
      size=10, color=GRAY, italic=True)

phases = [
    ("A", "AADT\nEstimation", NAVY, False,
     "Gradient boosting or linear regression\n"
     "on 286-station feature table.\n\n"
     "Predictors: functional class,\n"
     "seasonal amplitude, completeness,\n"
     "urban/rural, trust tier.\n\n"
     "Validate against official GDOT AADT\n"
     "using 27 reference stations as holdout."),
    ("B", "Gap\nFilling", STEEL, False,
     "Ratio-based imputation for CAUTION\n"
     "and seasonal-dropout stations.\n\n"
     "Donors: 27 reference station candidates\n"
     "+ 211 behavioral neighbor pairs.\n\n"
     "Validate by masking known-good\n"
     "periods and measuring MAPE by FC."),
    ("C", "Anomaly-\nAdjusted Counts", STEEL, False,
     "Exclude 37 unexplained anomaly-days\n"
     "from model training data.\n\n"
     "Run sensitivity tests with and without\n"
     "the 233 CAUTION-tier station-months.\n\n"
     "Apply holiday correction factors\n"
     "from the 2024 effect ratio analysis."),
    ("D", "Archetype\nModeling", GRAY, True,
     "DEFERRED -- cannot proceed yet.\n\n"
     "k-means (k=4) collapsed 77/78\n"
     "stations to 'Mixed'.\n\n"
     "Requires: multi-year directional\n"
     "profiles, vehicle class data from\n"
     "Tier 1 bins, full 207-station sample."),
]

box_w = 2.9; gap = 0.32; start_x = 0.4; box_t = 1.35; box_h = 5.2
for i, (letter, title, color, deferred, detail) in enumerate(phases):
    x = start_x + i * (box_w + gap)
    phase_box(sl, x, box_t, box_w, box_h, letter, title, detail, color, deferred)
    if i < len(phases) - 1:
        ax = x + box_w + 0.04
        txbox(sl, ax, box_t + box_h/2 - 0.2, gap - 0.04, 0.4,
              ">", size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

rect(sl, start_x + 3 * (box_w + gap) - 0.05, box_t, 0.05, box_h,
     fill=RGBColor(0xCC, 0xCC, 0xCC))
txbox(sl, start_x + 3 * (box_w + gap) + 0.05, box_t + box_h/2 - 0.12,
      0.5, 0.25, "LATER", size=7, bold=True, color=GRAY)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 15 — What We Built, What Comes Next  (reframed close)
# ═══════════════════════════════════════════════════════════════════════════
sl = add_slide()
header(sl, "What We Built, What Comes Next", NAVY)
footer(sl, 15)

# Left column: What We Built (positive close)
rect(sl, 0.2, 0.85, 6.35, 6.15, fill=RGBColor(0xF0, 0xF6, 0xF0))
rect(sl, 0.2, 0.85, 6.35, 0.32, fill=GREEN)
txbox(sl, 0.3, 0.88, 6.15, 0.26, "What We Built", size=13, bold=True, color=WHITE)

built_items = [
    ("243", "trusted stations validated and ready for modeling"),
    ("818K", "clean hourly records across 99 stations, full 2024"),
    ("286", "station feature table with 27 engineered predictors"),
    ("27", "reference stations identified as gap-filling donors"),
    ("6", "holiday effect ratios computed with FC breakdown"),
    ("7", "EDA analysis tracks completed and documented"),
]
for i, (num, desc) in enumerate(built_items):
    y = 1.4 + i * 0.72
    rect(sl, 0.35, y, 0.9, 0.52, fill=NAVY)
    txbox(sl, 0.35, y + 0.03, 0.9, 0.46, num, size=16, bold=True, color=WHITE,
          align=PP_ALIGN.CENTER)
    txbox(sl, 1.35, y + 0.06, 5.05, 0.46, desc, size=10, color=DARK, wrap=True)

rect(sl, 0.2, 5.72, 6.35, 0.62, fill=GREEN)
txbox(sl, 0.3, 5.78, 6.15, 0.22, "AADT modeling can begin now.", size=13, bold=True, color=WHITE)
txbox(sl, 0.3, 6.0, 6.15, 0.28,
      "The data is trustworthy, characterized, and ready.",
      size=10, color=LIGHT)

# Right column: What Comes Next
rect(sl, 6.78, 0.85, 6.35, 6.15, fill=RGBColor(0xF5, 0xF5, 0xFF))
rect(sl, 6.78, 0.85, 6.35, 0.32, fill=STEEL)
txbox(sl, 6.88, 0.88, 6.15, 0.26, "What Comes Next", size=13, bold=True, color=WHITE)

next_items = [
    ("Pipeline cap", "Expand hourly dataset from 99 to 207 eligible trusted stations"),
    ("Corridor scope", "Expand correlation analysis from 80 to ~230 eligible stations"),
    ("Archetype modeling", "Deferred until multi-year directional features are available"),
    ("Sparse stations", "5 chronic-sparse stations need field record investigation"),
    ("Directional splits", "NB/SB lane splits not yet in hourly dataset -- needed for directional models"),
]
for i, (label, desc) in enumerate(next_items):
    y = 1.35 + i * 0.88
    rect(sl, 6.93, y, 6.0, 0.78, fill=WHITE)
    rect(sl, 6.93, y, 0.1, 0.78, fill=STEEL)
    txbox(sl, 7.1, y + 0.05, 5.7, 0.28, label, size=10, bold=True, color=NAVY)
    txbox(sl, 7.1, y + 0.32, 5.7, 0.4, desc, size=9.5, color=DARK, wrap=True)

# ── Save ──────────────────────────────────────────────────────────────────
prs.save(str(OUT))
print(f"Saved: {OUT}  ({OUT.stat().st_size // 1024} KB)")
