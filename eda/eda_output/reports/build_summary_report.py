"""
Build GDOT EDA Final Summary Report as a polished PDF.
Content: the full Section B narrative (11 sections).
Format: A4 portrait, academic report style with cover page, TOC, running headers.
"""
from fpdf import FPDF
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent.parent
OUT    = BASE / "eda_output/reports/gdot_eda_summary_report.pdf"
INV2   = BASE / "outputs/figures/01_inventory"
MISS   = BASE / "eda_output/missingness"
PROF   = BASE / "eda_output/profiles"
TREN   = BASE / "eda_output/trends"
CORR   = BASE / "eda_output/corridors"
ANOM   = BASE / "eda_output/anomalies"

# ── colour palette ────────────────────────────────────────────────────────
NAVY   = (23,  54,  93)
STEEL  = (70, 130, 180)
LIGHT  = (220, 230, 242)
WHITE  = (255, 255, 255)
DARK   = (20,  20,  20)
GRAY   = (110, 110, 110)
GOLD   = (200, 155,  0)

PW, PH = 210, 297   # A4 portrait mm
ML, MR = 18, 18     # left / right margin
MT, MB = 28, 20     # top body start / bottom guard
TW = PW - ML - MR   # text width = 174 mm

class SummaryReport(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(ML, MT, MR)
        self.set_auto_page_break(True, margin=MB)
        self._current_section = ""

    # ── running header / footer ──────────────────────────────────────────
    def header(self):
        if self.page_no() <= 2:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, 0, PW, 10, "F")
        self.set_fill_color(*GOLD)
        self.rect(0, 0, 4, 10, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 7.5)
        self.set_xy(8, 2)
        self.cell(TW * 0.65, 6, "GDOT Traffic Dataset -- Exploratory Data Analysis", align="L")
        self.set_font("Helvetica", "I", 7.5)
        self.set_xy(8 + TW * 0.65, 2)
        self.cell(TW * 0.35 - 2, 6, self._current_section, align="R")
        self.set_xy(ML, 13)

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, PH - 10, PW, 10, "F")
        self.set_text_color(*LIGHT)
        self.set_font("Helvetica", "", 7)
        self.set_xy(ML, PH - 8)
        self.cell(TW * 0.7, 5, "Georgia Department of Transportation  |  2017-2024", align="L")
        self.set_xy(ML + TW * 0.7, PH - 8)
        self.cell(TW * 0.3, 5, f"Page {self.page_no()}", align="R")

    # ── helpers ──────────────────────────────────────────────────────────
    def h1(self, text, section_tag=""):
        self._current_section = section_tag or text
        self.ln(4)
        self.set_fill_color(*NAVY)
        self.rect(ML, self.get_y(), TW, 8, "F")
        self.set_fill_color(*GOLD)
        self.rect(ML, self.get_y(), 3, 8, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 12)
        self.set_x(ML + 5)
        self.cell(TW - 5, 8, text, align="L")
        self.ln(10)
        self.set_text_color(*DARK)

    def h2(self, text):
        self.ln(2)
        self.set_text_color(*STEEL)
        self.set_font("Helvetica", "B", 10.5)
        self.set_x(ML)
        self.cell(TW, 6, text, align="L")
        self.ln(1)
        self.set_fill_color(*LIGHT)
        self.rect(ML, self.get_y(), TW, 0.5, "F")
        self.ln(3)
        self.set_text_color(*DARK)

    def body(self, text, size=10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.set_x(ML)
        self.multi_cell(TW, 5.2, text, align="J")
        self.ln(2)

    def bullet(self, items, size=9.5, indent=4, fontsize=None):
        if fontsize is not None:
            size = fontsize
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        for item in items:
            self.set_x(ML + indent)
            self.cell(4, 5.2, "-")
            self.set_x(ML + indent + 4)
            self.multi_cell(TW - indent - 4, 5.2, item, align="J")
            self.ln(0.5)
        self.ln(1.5)

    def callout(self, text, color=LIGHT):
        self.ln(2)
        y0 = self.get_y()
        self.set_fill_color(*color)
        self.set_draw_color(*STEEL)
        self.rect(ML, y0, TW, 0, "F")  # will auto-size
        self.set_x(ML + 4)
        self.set_font("Helvetica", "I", 9.5)
        self.set_text_color(*GRAY)
        self.multi_cell(TW - 8, 5, text, align="J")
        h = self.get_y() - y0 + 2
        self.set_fill_color(*color)
        self.rect(ML, y0, TW, h, "F")
        # re-draw text over fill
        self.set_xy(ML + 4, y0 + 1)
        self.set_font("Helvetica", "I", 9.5)
        self.set_text_color(70, 70, 70)
        self.multi_cell(TW - 8, 5, text, align="J")
        self.ln(3)

    def _text_height(self, text, w, line_h):
        """Estimate multi_cell height by simulating word wrapping."""
        words = text.replace('\n', ' \n ').split(' ')
        current_w = 0
        lines = 1
        for word in words:
            if word == '\n':
                lines += 1
                current_w = 0
                continue
            ww = self.get_string_width(word)
            space = self.get_string_width(' ') if current_w > 0 else 0
            if current_w + space + ww > w:
                lines += 1
                current_w = ww
            else:
                current_w += space + ww
        return lines * line_h

    def kv_table(self, rows, col1_w=80, fontsize=9.5):
        line_h = 5.5
        col2_w = TW - col1_w
        for i, (k, v) in enumerate(rows):
            fill = LIGHT if i % 2 == 0 else WHITE
            y0 = self.get_y()
            # measure how tall this row needs to be
            self.set_font("Helvetica", "B", fontsize)
            h_k = self._text_height(f"  {k}", col1_w - 4, line_h)
            self.set_font("Helvetica", "", fontsize)
            h_v = self._text_height(str(v), col2_w - 4, line_h)
            row_h = max(h_k, h_v) + 3
            # draw fill background for the full row
            self.set_fill_color(*fill)
            self.rect(ML, y0, TW, row_h, "F")
            # write key
            self.set_text_color(*DARK)
            self.set_font("Helvetica", "B", fontsize)
            self.set_xy(ML + 2, y0 + 1.5)
            self.multi_cell(col1_w - 4, line_h, f"  {k}", align="L")
            # write value
            self.set_font("Helvetica", "", fontsize)
            self.set_xy(ML + col1_w + 2, y0 + 1.5)
            self.multi_cell(col2_w - 4, line_h, str(v), align="L")
            # advance to next row
            self.set_y(y0 + row_h)
        self.ln(3)

    def stat_box(self, label, value, note="", l=None):
        if l is None:
            l = self.get_x()
        box_w = 40
        self.set_fill_color(*NAVY)
        self.rect(l, self.get_y(), box_w, 18, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 15)
        self.set_xy(l, self.get_y() + 2)
        self.cell(box_w, 8, value, align="C")
        self.set_font("Helvetica", "", 7)
        self.set_xy(l, self.get_y() + 8)
        self.cell(box_w, 4, label, align="C")
        if note:
            self.set_xy(l, self.get_y() + 4)
            self.cell(box_w, 3, note, align="C")

    def place_img(self, path, w, caption=""):
        p = Path(path)
        if p.exists():
            x = ML + (TW - w) / 2
            self.image(str(p), x=x, w=w, keep_aspect_ratio=True)
        if caption:
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(*GRAY)
            self.set_x(ML)
            self.multi_cell(TW, 4, caption, align="C")
            self.set_text_color(*DARK)
        self.ln(3)

    def divider(self):
        self.ln(1)
        self.set_fill_color(*STEEL)
        self.rect(ML, self.get_y(), TW, 0.4, "F")
        self.ln(3)

# ═════════════════════════════════════════════════════════════════════════
rpt = SummaryReport()

# ── COVER PAGE ────────────────────────────────────────────────────────────
rpt.add_page()
rpt.set_auto_page_break(False)

rpt.set_fill_color(*NAVY)
rpt.rect(0, 0, PW, PH, "F")
rpt.set_fill_color(*GOLD)
rpt.rect(0, 0, 6, PH, "F")
rpt.set_fill_color(*STEEL)
rpt.rect(0, 95, PW, 1.5, "F")

rpt.set_text_color(*WHITE)
rpt.set_font("Helvetica", "B", 28)
rpt.set_xy(14, 52)
rpt.cell(PW, 12, "GDOT Traffic Dataset", align="L")
rpt.set_font("Helvetica", "B", 22)
rpt.set_xy(14, 68)
rpt.cell(PW, 10, "Exploratory Data Analysis", align="L")
rpt.set_font("Helvetica", "B", 16)
rpt.set_xy(14, 82)
rpt.cell(PW, 8, "Final Summary Report", align="L")

rpt.set_font("Helvetica", "", 11)
rpt.set_xy(14, 102)
rpt.cell(PW, 6, "Data Window:  2017 - 2024", align="L")
rpt.set_xy(14, 110)
rpt.cell(PW, 6, "Stations Analyzed:  286 of 330 cataloged stations", align="L")
rpt.set_xy(14, 118)
rpt.cell(PW, 6, "Analysis Tracks Completed:  7 of 7", align="L")
rpt.set_xy(14, 126)
rpt.cell(PW, 6, "Client:  Georgia Department of Transportation", align="L")
rpt.set_xy(14, 134)
rpt.cell(PW, 6, "Status:  EDA Complete -- Ready for AADT Modeling", align="L")

# key stat boxes on cover
rpt.set_fill_color(*STEEL)
rpt.rect(14, 158, PW - 20, 38, "F")
stats = [
    ("286", "Stations\nAnalyzed"),
    ("91.6%", "Station-Months\nComplete"),
    ("243", "Trusted\nStations"),
    ("818K", "Clean Hourly\nRecords (2024)"),
]
box_w = 38
gap   = (PW - 20 - box_w * 4) / 5
for i, (val, lbl) in enumerate(stats):
    bx = 14 + gap + i * (box_w + gap)
    rpt.set_fill_color(*NAVY)
    rpt.rect(bx, 162, box_w, 28, "F")
    rpt.set_text_color(*WHITE)
    rpt.set_font("Helvetica", "B", 17)
    rpt.set_xy(bx, 166)
    rpt.cell(box_w, 9, val, align="C")
    rpt.set_font("Helvetica", "", 7)
    rpt.set_xy(bx, 175)
    rpt.multi_cell(box_w, 3.5, lbl, align="C")

rpt.set_text_color(*LIGHT)
rpt.set_font("Helvetica", "", 8)
rpt.set_xy(14, PH - 20)
rpt.cell(PW - 20, 5,
         "Prepared using GDOT Continuous Count Station (CCS) data  |  Analysis conducted 2026",
         align="L")

rpt.set_auto_page_break(True, margin=MB)

# ── TABLE OF CONTENTS ──────────────────────────────────────────────────────
rpt.add_page()
rpt._current_section = "Contents"

rpt.set_fill_color(*NAVY)
rpt.rect(0, 0, PW, 14, "F")
rpt.set_fill_color(*GOLD)
rpt.rect(0, 0, 4, 14, "F")
rpt.set_text_color(*WHITE)
rpt.set_font("Helvetica", "B", 16)
rpt.set_xy(8, 4)
rpt.cell(PW, 7, "Table of Contents", align="L")
rpt.ln(20)

toc = [
    ("1", "Project Goal and Dataset Overview"),
    ("2", "Data Architecture: Three Tiers, Three Different Schemas"),
    ("3", "Station Inventory: Who Is in the Dataset"),
    ("4", "Completeness and Missingness: What Is Missing and Why"),
    ("5", "Baseline Traffic Behavior: What Normal Traffic Looks Like"),
    ("6", "Temporal Trends: COVID, Recovery, and Long-Run AADT"),
    ("7", "Holiday and Long Weekend Effects: Measured Patterns"),
    ("8", "Inter-Station Relationships: Corridors and Reference Stations"),
    ("9", "Anomaly Detection and Station Trustworthiness"),
    ("10", "Modeling Readiness: What Has Been Prepared"),
    ("11", "Known Gaps and Next Steps"),
]
rpt.set_text_color(*DARK)
for i, (num, title) in enumerate(toc):
    rpt.set_font("Helvetica", "B", 10.5)
    rpt.set_x(ML)
    rpt.cell(12, 8, num + ".")
    rpt.set_font("Helvetica", "", 10.5)
    rpt.cell(TW - 12, 8, title)
    if i < len(toc) - 1:
        rpt.set_fill_color(*LIGHT if i % 2 == 0 else WHITE)
        rpt.set_draw_color(*LIGHT)
    rpt.ln()

rpt.ln(6)
rpt.set_font("Helvetica", "I", 9)
rpt.set_text_color(*GRAY)
rpt.set_x(ML)
rpt.multi_cell(TW, 5,
    "This report documents the complete exploratory data analysis of the Georgia Department of "
    "Transportation (GDOT) Continuous Count Station (CCS) dataset. All findings are based on "
    "data analysis outputs produced by seven parallel EDA agents covering the 2017-2024 data window. "
    "Numerical results are drawn directly from analysis outputs and should not be modified without "
    "re-running the underlying computations.", align="J")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 1
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("1.  Project Goal and Dataset Overview", "1. Overview")
rpt.body(
    "The goal of this exploratory data analysis (EDA) was to develop a rigorous, evidence-based "
    "understanding of the Georgia Department of Transportation (GDOT) continuous count station (CCS) "
    "traffic dataset before any modeling work begins. The dataset spans eight years -- 2017 through "
    "2024 -- and covers traffic sensors distributed across Georgia's road network, from rural collectors "
    "to urban Interstate corridors."
)
rpt.body(
    "The EDA was organized into seven parallel analysis tracks: data inventory, missingness audit, "
    "traffic behavior profiling, temporal trend analysis, inter-station corridor relationships, anomaly "
    "detection and trustworthiness assessment, and modeling-ready feature engineering. Each track "
    "produced structured outputs -- CSV tables, figures, and written reports -- that are synthesized "
    "here into a single consolidated summary."
)
rpt.body(
    "The central question guiding the entire EDA was: Is this dataset trustworthy, well-understood, "
    "and sufficiently characterized to support AADT estimation and gap-filling models? The answer, "
    "with important qualifications documented throughout this report, is yes."
)

rpt.ln(2)
rpt.set_font("Helvetica", "B", 10)
rpt.set_text_color(*NAVY)
rpt.set_x(ML)
rpt.cell(TW, 6, "Dataset at a Glance", align="L")
rpt.ln(7)
rpt.kv_table([
    ("Stations in catalog",       "330  (286 stations appear in at least one data tier)"),
    ("Data tiers",                "3  (2024 5-min / 2022-23 5-min / 2017-22 Hourly)"),
    ("Coverage window",           "2017 through 2024  (8 calendar years)"),
    ("Total station-months",      "21,837"),
    ("Complete station-months",   "19,998  (91.6% of station-months meet the >=80% coverage threshold)"),
    ("Fleet-wide missingness",    "8.4%"),
    ("Trusted stations",          "243 of 286  (84.9% of the fleet)"),
    ("Clean hourly records",      "818,645  across 99 trusted stations for the 2024 calendar year"),
], col1_w=68)

rpt.place_img(INV2 / "01_station_catalog_profiling.png", TW,
    "Figure 1: Station catalog overview showing tier presence, functional class, "
    "and urban-rural breakdown across the 286-station fleet.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 2
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("2.  Data Architecture: Three Tiers, Three Different Schemas", "2. Architecture")
rpt.body(
    "The GDOT CCS dataset does not exist as a single unified table. It is organized into three "
    "distinct data tiers, each covering a different time window and collected at a different resolution "
    "and stratification level. Understanding these differences is essential before any cross-tier "
    "comparison or longitudinal analysis is attempted."
)

rpt.h2("Tier Structure")
rpt.kv_table([
    ("Tier 1 (2024)",
     "5-minute resolution. Directional (N/S/E/W). Includes speed bin distributions (<10 to >80 mph) "
     "and weight class bins. Station IDs are 12-digit zero-padded COSIT values in filenames."),
    ("Tier 2 (2022-2023)",
     "5-minute resolution. Lane-level stratification (e.g., Ln 1 NB). No speed or weight bins. "
     "Station IDs in the standard XXX-XXXX format."),
    ("Tier 3 (2017-2022)",
     "Hourly resolution. Directional stratification. Includes average speed and VolumeQC/ClassQC "
     "quality-control flags. No bin distributions."),
], col1_w=40, fontsize=9.5)

rpt.h2("Why Cross-Tier Joining Is Difficult")
rpt.body(
    "Joining data across tiers is non-trivial for three distinct reasons. First, the station ID "
    "format changes between Tier 1 (twelve-digit COSIT) and Tiers 2 and 3 (XXX-XXXX), requiring "
    "a derivation mapping that is not always reliable. Two stations use non-standard 'w'-suffix IDs "
    "(021-w334 and 185-w227) that cannot be matched to either format without manual lookup. "
    "Second, temporal resolution changes from hourly to five-minute between Tier 3 and Tiers 1 and 2, "
    "which means direct time-series comparisons require explicit resampling. Third, Tier 2 dropped "
    "directional stratification in favor of lane-level detail, making it impossible to directly compare "
    "directional volumes between 2022-2023 and 2024 without lane-aggregation assumptions."
)
rpt.callout(
    "Practical implication: Any modeling pipeline that joins data across tiers must explicitly "
    "handle the ID format mismatch, the resolution change, and the stratification change. "
    "Failure to do so will produce silent join failures and incorrect merged datasets."
)

rpt.h2("Tier Overlap Summary")
rpt.kv_table([
    ("Stations in all three tiers", "225  (78.7% of the 286-station working set)"),
    ("Stations in exactly two tiers", "27"),
    ("Stations in only one tier",    "34  (limited longitudinal history)"),
    ("Tier 1 complete-month rate",   "94.9%"),
    ("Tier 2 complete-month rate",   "93.3%"),
    ("Tier 3 complete-month rate",   "98.8%"),
], col1_w=80)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 3
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("3.  Station Inventory: Who Is in the Dataset", "3. Inventory")
rpt.body(
    "The canonical station catalog contains 330 stations, of which 286 appear in at least one data "
    "tier and have usable records. Of those 286, 225 stations (78.7%) appear in all three tiers, "
    "making them the most complete and comparable stations for longitudinal analysis."
)

rpt.h2("Functional Class Distribution")
rpt.body(
    "The fleet is dominated by Interstate stations. Of the 286 analyzed stations: 139 (42%) are "
    "FC1 Interstate, 77 (23%) are FC3 Other Principal Arterial, 52 (18%) are FC4 Minor Arterial, "
    "34 (12%) are FC5 Major Collector, and 23 (8%) are FC2 Freeways or Expressways. This Interstate "
    "concentration shapes every downstream analysis: Interstate stations carry higher volumes, show "
    "lower weekday-to-weekend ratios, and have different missingness patterns compared to arterials "
    "and collectors."
)

rpt.h2("Urban-Rural Split")
rpt.body(
    "The urban-rural split is approximately 70% urban and 30% rural by station count. Urban "
    "Interstate stations form the single largest subcategory at 115 stations, followed by Urban "
    "Other Principal Arterial (52) and Urban Minor Arterial (38). Rural Other Principal Arterial "
    "(25) and Rural Interstate (24) make up the largest rural subcategories."
)

rpt.h2("Active Station Trends Over Time")
rpt.body(
    "Active station counts have declined slightly over the data window, from 258 active stations "
    "in 2018 to 233 in 2024. This decline is gradual and likely reflects sensor retirements and "
    "station relocations rather than systematic data coverage loss. The mean number of complete "
    "months per station across all tiers is 72.9, with a median of 84.0, confirming that most "
    "stations have long and relatively continuous coverage histories."
)

rpt.place_img(INV2 / "04_stations_per_year.png", TW * 0.85,
    "Figure 2: Number of active stations per year, 2017-2024. Gradual decline from 258 (2018) "
    "to 233 (2024) reflects sensor retirements and station relocations.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 4
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("4.  Completeness and Missingness: What Is Missing and Why", "4. Missingness")

rpt.h2("Fleet-Wide Completeness")
rpt.body(
    "The missingness audit covered all 286 stations across 21,837 station-months from 2017 through "
    "2024. A station-month was classified as COMPLETE if at least 80% of expected five-minute or "
    "hourly bins contained valid data. Under this threshold, 19,998 station-months (91.6%) are "
    "COMPLETE, 1,237 station-months (5.7%) are ABSENT, and the overall fleet-wide missingness rate "
    "is 8.4%."
)
rpt.body(
    "At the station level, the reliability picture is reassuring: 210 stations (73.4%) are "
    "classified as 'always on,' meaning at least 90% of their months are complete. Only 5 stations "
    "(1.8%) are chronically sparse, with fewer than 40% complete months across their operational history."
)

rpt.h2("Outage Structure and Run Lengths")
rpt.body(
    "Outage run-length analysis reveals important structure beneath the headline number. Of 226 "
    "identified outage sequences, 52% are single-month gaps -- consistent with routine maintenance "
    "or brief sensor failures. However, 73 runs (32%) exceed six months, with the longest spanning "
    "60 consecutive absent months. These long outages almost certainly represent sensor replacement "
    "cycles or extended decommissioning, not random data loss."
)

rpt.h2("Year-over-Year Missingness Trends")
rpt.body(
    "Missingness varies substantially over time. The highest annual rate was in 2017 (13.6%), "
    "consistent with incomplete initial export coverage at the start of the data window. A secondary "
    "spike appeared in 2022-2023 (12.0% and 11.8%), likely reflecting the transition from directional "
    "hourly to five-minute lane-level collection -- a period when sensor retirements and "
    "re-instrumentation may have temporarily reduced coverage. By 2024, the rate recovered to 7.8%."
)
rpt.callout(
    "Interpretation: These temporal patterns are inconsistent with missing-completely-at-random "
    "(MCAR) and are better described as structured, operationally driven absences. Any imputation "
    "or gap-filling approach must account for this structure rather than treating missing data as random."
)

rpt.place_img(MISS / "fig_missingness_by_year.png", TW * 0.82,
    "Figure 3: Fleet-wide missingness rate by year. Peaks in 2017 (initial coverage) and "
    "2022-23 (pipeline transition). Recovery to 7.8% in 2024.")

rpt.h2("Functional Class Missingness Disparities")
rpt.body(
    "By functional class, FC1 Interstate and FC2 Freeway stations show the highest missingness "
    "rates -- 13.5% and 14.6% respectively -- which is counterintuitive for high-priority "
    "infrastructure. One plausible explanation is methodological: multi-lane sensors produce a "
    "larger number of expected bins per interval, making the 80% completeness threshold harder to "
    "satisfy even when sensors are functioning normally. This possibility should be tested before "
    "concluding that Interstate data is structurally lower quality. Arterial and collector stations "
    "(FC3-FC5) show substantially lower missingness, ranging from 3.2% to 5.4%."
)

rpt.h2("Sub-Daily Patterns")
rpt.body(
    "Sub-daily analysis of 2024 data showed that missingness peaks at hour 6 (early morning) and "
    "reaches its minimum at hour 16 (the PM peak). Day-of-week differences are small but nonzero, "
    "with Wednesday showing slightly elevated missingness. Additionally, 6.48% of 2024 five-minute "
    "bins show a zero vehicle count with coverage above 50% -- a pattern that may reflect genuine "
    "overnight zero-volume periods at rural sites, but warrants additional review at urban locations "
    "during normal traffic hours."
)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 5
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("5.  Baseline Traffic Behavior: What Normal Traffic Looks Like", "5. Traffic Behavior")
rpt.body(
    "Traffic behavior profiles were computed from 2024 five-minute CCS data using a stratified "
    "sample of 100 stations. Only intervals with at least 50% bin coverage were retained."
)

rpt.h2("Volume Distributions")
rpt.body(
    "The median daily volume across all sampled stations is 22,830 vehicles per day. The mean "
    "(45,223 vehicles per day) substantially exceeds the median, driven by a small number of "
    "high-volume freeway and expressway stations. This skewness is important to account for in "
    "modeling -- a small number of stations carry disproportionate traffic load."
)
rpt.kv_table([
    ("FC2 Freeways/Expressways",  "~110,000 veh/day median"),
    ("FC1 Interstate",            "~52,000 veh/day median"),
    ("FC3 Other Principal Arterial","~19,000 veh/day median"),
    ("FC4 Minor Arterial",        "~12,000 veh/day median"),
    ("FC5 Major Collector",       "~1,900 veh/day median"),
], col1_w=72, fontsize=9.5)

rpt.h2("Weekday vs. Weekend Ratios")
rpt.body(
    "The fleet-wide weekday-to-weekend ratio is 1.25, meaning the average station carries 25% more "
    "traffic on weekdays than on weekends. This ratio varies meaningfully by functional class: "
    "Interstate stations show a ratio of only 1.08, indicating nearly uniform seven-day use -- "
    "consistent with a mix of commuter, freight, and recreational travel. Arterial and collector "
    "stations show ratios of 1.35 to 1.44, consistent with predominantly commuter-oriented use."
)

rpt.h2("AM and PM Peak Hours")
rpt.body(
    "Peak hours are stable and consistent across functional classes and seasons. The AM peak is "
    "7:00 and the PM peak is 17:00 for the majority of stations. This stability is an important "
    "validation result: it confirms that sensor readings capture real traffic behavior, and it "
    "provides a strong foundation for using peak-hour features in future AADT models."
)

rpt.h2("Seasonality")
rpt.body(
    "Based on 2023 data from 30 stations, October is the peak traffic month (Seasonal Index = "
    "1.036) and January is the trough (SI = 0.928), yielding a seasonal amplitude of approximately "
    "+/-10% around the annual mean. Rural stations on lower-functional-class roads show stronger "
    "seasonality than urban Interstate stations."
)

rpt.place_img(PROF / "fig_hourly_profile_by_fc.png", TW * 0.85,
    "Figure 4: Average weekday hourly traffic volume profiles by functional class. "
    "AM peak at 07:00 and PM peak at 17:00 are stable across all classes.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 6
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("6.  Temporal Trends: COVID, Recovery, and Long-Run AADT", "6. Temporal Trends")
rpt.body(
    "Annual average daily traffic (AADT) trends were analyzed using a June reference-month proxy "
    "for 30 stations across 2018-2023. June was chosen as the reference month because it falls "
    "close to the annual average with relatively low seasonal distortion, providing a stable "
    "single-month proxy for full-year AADT without requiring a complete calendar year of data. "
    "The mean June daily volume across selected stations was 26,692 vehicles per day."
)

rpt.h2("COVID-19 Impact and Recovery")
rpt.body(
    "The most prominent feature of the trend is the COVID-19 impact in 2020. The 2019 to 2020 "
    "median volume drop across the 30-station sample was approximately 8.6%. This drop is visible "
    "across all functional classes, though timing and magnitude vary slightly. Post-COVID recovery "
    "is clearly visible by 2021 and 2022, with most stations returning to near-2019 volume levels "
    "by 2022. Freeways recovered fastest; collectors showed the slowest and most uneven recovery."
)

rpt.h2("Why June Is Used as the AADT Proxy")
rpt.body(
    "Using a single reference month rather than the full calendar year is a practical trade-off. "
    "June is the least seasonally biased month in Georgia -- its traffic volume is close to the "
    "annual average -- and it avoids the requirement that a station have a complete calendar year "
    "of data to participate in the analysis. This approach introduces some inaccuracy for stations "
    "with high seasonal amplitude (>0.4), where June may deviate from the true annual mean. "
    "Seasonal adjustment factors from the seasonal index table are available to correct for this."
)

rpt.h2("Peak-Hour Stability")
rpt.body(
    "Peak-hour stability analysis across January, April, July, and October of 2023 confirms that "
    "the AM peak at 7:00 and PM peak at 17:00 are robust across seasons. This finding is important "
    "for AADT modeling because it means peak-hour features can be treated as stable structural "
    "properties of each station rather than time-varying inputs."
)

rpt.place_img(TREN / "fig_aadt_trend_2017_2024.png", TW * 0.9,
    "Figure 5: AADT proxy (June mean daily volume) by functional class, 2018-2023. "
    "COVID-19 impact clearly visible in 2020. Recovery observed by 2021-2022.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 7
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("7.  Holiday and Long Weekend Effects: Measured Patterns", "7. Holiday Effects")
rpt.body(
    "Holiday and long-weekend effects were computed from the 2024 clean hourly dataset (99 trusted "
    "stations) using event flags from the all_events_2024 database. For each major holiday, daily "
    "volume at each station was compared to the median volume on the same day of the week from "
    "non-event control weeks within an eight-week window. The effect ratio is defined as "
    "holiday_volume / median(control_volume) -- values below 1.0 indicate a traffic reduction."
)

rpt.h2("Major Holiday Effects")
rpt.kv_table([
    ("New Year's Day",   "Effect ratio 0.69-0.88 by FC. Significant reduction across all station types."),
    ("Memorial Day",     "Effect ratio 0.80-0.91. Moderate reduction; travel partially offsets commuter drop."),
    ("Independence Day", "Effect ratio 0.63-0.79. Largest single-day reduction among major holidays."),
    ("Labor Day",        "Effect ratio 0.85-0.90. Similar to Memorial Day; end-of-summer travel effect."),
    ("Thanksgiving",     "Effect ratio 0.59-0.76. Strong reduction consistent with reduced commercial travel."),
    ("Christmas",        "Effect ratio 0.58-0.70. Strongest sustained reduction of any holiday category."),
], col1_w=52, fontsize=9.5)

rpt.body(
    "Interstate stations consistently show the smallest holiday reduction (highest ratios), "
    "reflecting that freight and through travel continues on holidays even as local commuter traffic "
    "falls. Arterial and collector stations show larger holiday drops, consistent with their greater "
    "dependence on local commuter traffic."
)

rpt.h2("Long Weekend Patterns")
rpt.body(
    "Long-weekend analysis examined the full Thursday-to-Tuesday window around Memorial Day, "
    "Independence Day, and Labor Day. Results show a clear pattern: traffic drops sharply on the "
    "Friday before a holiday Monday and recovers gradually through the following Tuesday. "
    "Independence Day (which falls mid-week) shows a more concentrated single-day drop rather than "
    "a gradual long-weekend pattern."
)
rpt.callout(
    "Modeling implication: If daily traffic volumes are used to estimate annual AADT, holiday days "
    "must be down-weighted or excluded -- otherwise AADT will be underestimated. The effect ratios "
    "computed here provide direct quantitative adjustment factors for this purpose."
)

rpt.place_img(TREN / "fig_holiday_effect.png", TW,
    "Figure 6: Holiday effect ratios by functional class for six major holidays in 2024. "
    "All ratios below 1.0 indicate below-normal traffic volume. "
    "Independence Day, Thanksgiving, and Christmas show the largest reductions.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 8
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("8.  Inter-Station Relationships: Corridors and Reference Stations", "8. Corridors")
rpt.body(
    "Corridor and inter-station relationship analysis used the top 80 stations by data completeness, "
    "constructing a daily volume matrix for the full 2024 calendar year. Pairwise Pearson "
    "correlations were computed for all station pairs with at least 180 overlapping observation days."
)

rpt.h2("Pairwise Correlation Results")
rpt.kv_table([
    ("Valid station pairs",          "2,848  (>=180 overlapping observation days)"),
    ("Mean Pearson r",               "0.573"),
    ("Median Pearson r",             "0.636"),
    ("Range",                        "-0.24 to 0.993"),
    ("High-correlation pairs (r>0.85)", "411  (14.4% of all valid pairs)"),
], col1_w=82)

rpt.body(
    "The moderately strong fleet-wide correlation structure reflects that most Georgia traffic "
    "stations respond to the same broad demand patterns -- commuter rhythms, seasonal cycles, "
    "and economic activity. The range from -0.24 to 0.993 shows meaningful behavioral variation "
    "across station types and locations, which is important for corridor-specific imputation."
)

rpt.h2("Corridor Clusters and Behavioral Neighbors")
rpt.body(
    "Hierarchical clustering at a distance threshold corresponding to r > 0.85 produced 44 cluster "
    "IDs, of which 7 are multi-station corridor clusters and 37 are singletons. The 7 corridor "
    "clusters represent groups of stations with strongly coherent daily volume patterns -- these "
    "are the best candidates for corridor-level imputation and cross-validation. Additionally, 211 "
    "behavioral neighbor pairs (r > 0.7 and within 50 km) were identified across 705 individual "
    "station-neighbor relationships, providing a broader pool of imputation candidates."
)

rpt.h2("Reference Station Candidates")
rpt.body(
    "27 stations were identified as reference station candidates, having passed all five quality "
    "criteria: at least 85% data completeness, at least 10 complete months, at least 2 behavioral "
    "neighbors, data present in all 3 tiers, and membership in a multi-station cluster. These 27 "
    "stations are geographically distributed across 15 Georgia counties. The top candidates by "
    "behavioral neighbor count are station 089-3323 in DeKalb County (10 behavioral neighbors) "
    "and 057-0341 in Cherokee County (8 behavioral neighbors)."
)
rpt.callout(
    "Coverage caveat: The correlation analysis covers only the top 80 stations by completeness. "
    "Approximately 150 additional eligible stations have not been assessed. The 27 reference "
    "station candidates likely underrepresent the true pool of high-quality imputation donors."
)

rpt.place_img(CORR / "fig_correlation_heatmap.png", TW * 0.85,
    "Figure 7: Pairwise Pearson correlation matrix for the top 80 stations by completeness, 2024. "
    "Block-diagonal structure reflects geographic and functional class clustering.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 9
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("9.  Anomaly Detection and Station Trustworthiness", "9. Anomalies")
rpt.body(
    "Anomaly detection was applied to 58 stations with accessible raw 2024 five-minute data files. "
    "Two methods were used: an IQR-based rule flagging days with volume below median - 3*IQR or "
    "above median + 3*IQR, and a low-volume rule flagging days with volume below 10% of the "
    "station's annual median."
)

rpt.h2("Anomaly Detection Results")
rpt.kv_table([
    ("Total anomaly-days detected",      "391  across 58 stations"),
    ("Explained by event flags",         "354  (90.5%)"),
    ("Unexplained anomaly-days",         "37  (9.5%)"),
    ("Event flags used for explanation", "Holiday, Volume Bad, Outlier, Atypical, Roadworks, Closure, Accident"),
], col1_w=68, fontsize=9.5)

rpt.body(
    "The high explained rate of 90.5% is a positive finding. It means the GDOT event flag system "
    "is functioning as a reliable indicator of known disruptions. The 37 unexplained anomaly-days "
    "may reflect real traffic events not captured in the event log -- weather incidents, unreported "
    "road closures, or unusual local events -- rather than sensor malfunctions."
)

rpt.h2("Station-Month and Station-Level Trust Tiers")
rpt.body(
    "Station-month trustworthiness was assessed across all 286 stations using a combination of "
    "coverage proxy scores and, where available, volume-level anomaly detection results."
)
rpt.kv_table([
    ("TRUSTED station-months",   "19,963  (96.9% of all station-months)"),
    ("CAUTION station-months",   "233  (1.1%)"),
    ("EXCLUDED station-months",  "404  (2.0%)"),
    ("TRUSTED stations",         "243  (84.9% of the 286-station fleet)"),
    ("CAUTION stations",         "36  (12.6%)  -- usable in sensitivity analyses"),
    ("EXCLUDED stations",        "7  (2.5%)  -- require manual investigation"),
], col1_w=68, fontsize=9.5)

rpt.callout(
    "Note: The trustworthiness assessment for 228 of 286 stations (those outside the 58-station "
    "raw-data sample) relies on coverage proxy scores rather than direct volume-level anomaly "
    "detection. This may underestimate anomaly risk for those stations, and direct anomaly "
    "detection should be extended to the full fleet before final modeling decisions are made."
)

rpt.place_img(ANOM / "fig_trust_tier_distribution.png", TW * 0.7,
    "Figure 8: Distribution of station trust tiers across the 286-station fleet. "
    "243 stations (84.9%) are in the TRUSTED tier.")

# ═════════════════════════════════════════════════════════════════════════
# SECTION 10
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("10.  Modeling Readiness: What Has Been Prepared", "10. Modeling Readiness")

rpt.h2("Clean Hourly 2024 Dataset")
rpt.body(
    "The primary modeling-ready dataset is the clean hourly 2024 record set: 818,645 hourly "
    "records across 99 trusted stations. Each record includes station ID, date, hour of day, day "
    "of week, month, weekday flag, total vehicle volume, vehicle class counts (F1-F15), hourly "
    "coverage percentage, and an imputation flag. The coverage threshold for inclusion was 50%; "
    "hours with fewer than 6 valid five-minute bins are flagged but retained. Median hourly volume "
    "is 580 vehicles per hour; the maximum is 17,822."
)

rpt.h2("Station Feature Table")
rpt.body(
    "The 286-station feature table contains 27 features per station, including functional class, "
    "urban-rural classification, AADT 2024 estimate, seasonal amplitude, number of data sources, "
    "percent complete, trust tier, anomaly count, AM and PM peak hours, and a heavy vehicle share "
    "estimate. This table covers all stations regardless of trust tier, enabling downstream "
    "filtering by any quality criterion. The AADT 2024 estimate is computed as median daily volume "
    "times 365 -- a June-reference-free proxy that degrades for high-seasonality stations "
    "(seasonal amplitude > 0.4)."
)

rpt.h2("Recommended Modeling Resolution")
rpt.body(
    "The recommended modeling resolution is hourly. This granularity captures diurnal patterns "
    "(AM and PM peaks, overnight troughs) that are essential for AADT estimation, while smoothing "
    "the noise present in individual five-minute intervals. Five-minute data is too noisy for "
    "direct modeling; daily aggregation loses the peak-hour structure that differentiates station "
    "types."
)

rpt.h2("Recommended Modeling Phases")
rpt.bullet([
    "Phase A -- AADT Estimation: Use gradient boosting or linear regression on the 286-station "
    "feature table, with functional class, seasonal amplitude, and completeness as primary "
    "predictors. Validate against official GDOT AADT reports using the 27 reference station "
    "candidates as holdout points.",
    "Phase B -- Gap Filling: For CAUTION-tier and seasonal-dropout stations, apply ratio-based "
    "imputation using the 27 reference station candidates as primary donors, with the 211 "
    "behavioral neighbor pairs as the secondary donor pool.",
    "Phase C -- Anomaly-Adjusted Counts: Exclude the 37 unexplained anomaly-days from model "
    "training and run sensitivity tests on CAUTION-tier station-months to quantify their influence.",
    "Phase D -- Archetype Modeling (DEFERRED): k-means clustering collapsed 77/78 stations to "
    "'Mixed.' Deferred until multi-year directional profiles, vehicle class distributions, and "
    "the full 207-station eligible sample are available.",
], fontsize=9.5)

rpt.kv_table([
    ("station_master_table.csv",         "286 stations x metadata + completeness + tier flags"),
    ("station_missingness_scorecard.csv","Per-station outage style and completeness metrics"),
    ("station_daily_volume_summary.csv", "Per-station volume statistics (100-station, 2024)"),
    ("aadt_trends_by_station.csv",       "Station x year AADT proxy (30-station, 2018-2023)"),
    ("reference_station_candidates.csv", "27 top reference / imputation stations"),
    ("trusted_station_list.csv",         "243 HIGH-trust stations"),
    ("clean_hourly_2024_trusted.csv",    "818,645 hourly records, 99 stations, 26 columns"),
    ("station_feature_table.csv",        "286 stations x 27 modeling features"),
], col1_w=80, fontsize=9)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 11
# ═════════════════════════════════════════════════════════════════════════
rpt.add_page()
rpt.h1("11.  Known Gaps and Next Steps", "11. Gaps & Next Steps")
rpt.body(
    "Four significant gaps remain before the analysis is fully complete. Each is documented here "
    "with its current status, the action required to resolve it, and the impact on downstream "
    "modeling if left unresolved."
)

rpt.h2("Gap 1: Incomplete Hourly Dataset Coverage")
rpt.body(
    "The current clean hourly dataset covers 99 of 207 eligible trusted stations due to a "
    "100-station pipeline cap imposed during processing. The remaining 108 stations meet all "
    "trust and coverage criteria but were not processed. Removing this cap and reprocessing "
    "would expand coverage to the full eligible population, improving model robustness and "
    "enabling more reliable corridor imputation. The expected output size is approximately "
    "200 MB as CSV, or 40 MB if converted to Parquet format using pyarrow."
)

rpt.h2("Gap 2: Incomplete Corridor Analysis")
rpt.body(
    "The pairwise correlation matrix and reference station pool were derived from only the top "
    "80 stations by completeness. Approximately 150 additional eligible stations have not been "
    "assessed for corridor membership or behavioral neighbor suitability. Expanding the analysis "
    "-- with a relaxed minimum overlap threshold of 90 overlapping days rather than 180 -- would "
    "likely identify additional imputation donors and improve gap-filling quality, particularly "
    "for stations in rural or lower-completeness areas."
)

rpt.h2("Gap 3: Archetype Modeling Is Not Yet Viable")
rpt.body(
    "The k-means clustering collapsed to a single dominant 'Mixed' category, producing labels "
    "that carry no analytical value. This result is not a modeling failure -- it is a data "
    "finding. It tells us that 2024-only features and a 100-station sample are insufficient to "
    "discriminate behavioral archetypes. Archetype-level modeling should be deferred until "
    "multi-year directional profiles, vehicle class distributions from Tier 1 speed and weight "
    "bins, and the full 207-station sample are available."
)

rpt.h2("Gap 4: Chronic-Sparse and Non-Standard Stations")
rpt.body(
    "Five stations with fewer than 40% complete months have unknown operational status -- it is "
    "unclear whether they are decommissioned, relocated, or persistently failing sensors. Two "
    "additional stations use non-standard 'w'-suffix ID formats that prevent reliable cross-tier "
    "joins without manual lookup. Both groups require investigation against GDOT field maintenance "
    "records before any inclusion or definitive exclusion from modeling."
)

rpt.h2("Summary: What Is Ready and What Needs Work")
rpt.kv_table([
    ("Ready now",
     "AADT estimation using 286-station feature table; gap-filling using 27 reference stations; "
     "anomaly-adjusted count modeling; holiday effect adjustments for 99-station sample"),
    ("Needs pipeline fix",
     "Expand hourly dataset from 99 to 207 stations (remove cap); expand corridor analysis "
     "from 80 to 230 eligible stations"),
    ("Needs additional data",
     "Archetype modeling requires multi-year directional profiles and vehicle class distributions"),
    ("Needs manual investigation",
     "5 chronic-sparse stations and 2 non-standard ID stations require field record review"),
], col1_w=48, fontsize=9.5)

rpt.ln(4)
rpt.set_fill_color(*LIGHT)
rpt.rect(ML, rpt.get_y(), TW, 22, "F")
rpt.set_fill_color(*NAVY)
rpt.rect(ML, rpt.get_y(), 3, 22, "F")
rpt.set_text_color(*NAVY)
rpt.set_font("Helvetica", "B", 10.5)
rpt.set_xy(ML + 6, rpt.get_y() + 3)
rpt.cell(TW - 10, 6, "Conclusion", align="L")
rpt.set_font("Helvetica", "", 9.5)
rpt.set_text_color(*DARK)
rpt.set_xy(ML + 6, rpt.get_y() + 6)
rpt.multi_cell(TW - 10, 5,
    "The GDOT traffic dataset is well-characterized, largely reliable, and ready for AADT "
    "estimation. 243 trusted stations with 818,000 clean hourly records and a 286-station feature "
    "table provide a strong foundation. Holiday effects are now quantified. The four gaps "
    "documented above are manageable engineering and data tasks, not fundamental data quality "
    "failures. Addressing them will improve model coverage and robustness but is not required "
    "before initial AADT modeling can begin.",
    align="J")

# ── Save ──────────────────────────────────────────────────────────────────
rpt.output(str(OUT))
print(f"Saved: {OUT}  ({OUT.stat().st_size // 1024} KB)")
