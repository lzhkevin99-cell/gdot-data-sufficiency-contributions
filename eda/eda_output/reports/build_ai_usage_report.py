"""
Generates a polished PDF summarizing the AI-assisted subagent pipeline used
in the GDOT EDA project -- focused on technical functionality and agent design.
Output: eda_output/reports/gdot_ai_usage_summary.pdf
"""
from fpdf import FPDF
from pathlib import Path

OUT = Path(__file__).resolve().parent
PDF_PATH = OUT / "gdot_ai_usage_summary.pdf"

NAVY   = (30,  50,  90)
GOLD   = (200, 160,  40)
WHITE  = (255, 255, 255)
LIGHT  = (245, 247, 251)
LGRAY  = (210, 215, 225)
GRAY   = (120, 120, 120)
BLACK  = (30,  30,  30)
ACCENT = (52,  90,  160)
GREEN  = (38, 120,  75)
TEAL   = (28, 108, 118)

ML = 18
MR = 18
PW = 210
PH = 297
TW = PW - ML - MR


class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(ML, 20, MR)
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, 0, PW, 12, "F")
        self.set_fill_color(*GOLD)
        self.rect(0, 11.5, PW, 0.8, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*WHITE)
        self.set_y(3)
        self.cell(0, 6, "GDOT EDA Project  |  AI-Assisted Subagent Pipeline", align="L")
        self.set_y(20)
        self.set_text_color(*BLACK)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*NAVY)
        self.rect(0, PH - 14, PW, 14, "F")
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*WHITE)
        self.cell(0, 14, f"Page {self.page_no()}", align="C")

    def rule(self, color=GOLD):
        self.set_draw_color(*color)
        self.set_line_width(0.6)
        self.line(ML, self.get_y(), ML + TW, self.get_y())
        self.ln(3)
        self.set_line_width(0.2)

    def section_heading(self, text):
        self.ln(4)
        self.set_font("Helvetica", "B", 13.5)
        self.set_text_color(*NAVY)
        self.set_x(ML)
        self.multi_cell(TW, 8, text)
        self.rule()

    def body(self, text, size=10, indent=0):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*BLACK)
        self.set_x(ML + indent)
        self.multi_cell(TW - indent, 5.8, text)
        self.ln(1)

    def bullet(self, label, text, size=9.5, indent=4, label_w=0):
        self.set_x(ML + indent)
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*GOLD)
        self.cell(3.5, 5.5, "-")
        if label_w > 0:
            self.set_font("Helvetica", "B", size)
            self.set_text_color(*NAVY)
            self.cell(label_w, 5.5, label)
            self.set_font("Helvetica", "", size)
            self.set_text_color(*BLACK)
            self.multi_cell(TW - indent - 3.5 - label_w, 5.5, text)
        else:
            self.set_font("Helvetica", "", size)
            self.set_text_color(*BLACK)
            self.multi_cell(TW - indent - 3.5, 5.5, label + text)
        self.ln(0.5)

    def callout(self, text, bg=LIGHT, bar=ACCENT):
        self.ln(2)
        self.set_font("Helvetica", "I", 9.5)
        # measure lines
        lines = max(1, len(text) // 85 + text.count("\n") + 1)
        h = lines * 5.5 + 7
        y0 = self.get_y()
        self.set_fill_color(*bg)
        self.set_draw_color(*bar)
        self.set_line_width(0.4)
        self.rect(ML, y0, TW, h, "DF")
        self.set_fill_color(*bar)
        self.rect(ML, y0, 1.2, h, "F")
        self.set_xy(ML + 4, y0 + 3)
        self.set_text_color(*BLACK)
        self.multi_cell(TW - 6, 5.5, text)
        self.set_y(y0 + h + 2)

    # ── agent card using natural flow ────────────────────────────────────────
    def agent_card(self, number, name, role, color,
                   focus_items, deliverables, result):
        self.ln(3)
        # header bar
        self.set_fill_color(*color)
        self.rect(ML, self.get_y(), TW, 11, "F")
        # number badge
        self.set_fill_color(*GOLD)
        self.rect(ML + 2, self.get_y() + 1.5, 8, 8, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.set_xy(ML + 2, self.get_y() + 1.5)
        self.cell(8, 8, str(number), align="C")
        # name + role
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*WHITE)
        self.set_xy(ML + 13, self.get_y() - 7.5)
        self.cell(0, 5, name)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(200, 215, 240)
        self.set_xy(ML + 13, self.get_y() + 5)
        self.cell(0, 4, role)
        self.ln(12)

        # body background
        body_start = self.get_y()
        self.set_fill_color(*LIGHT)
        self.set_x(ML)

        # left stripe
        def left_stripe(h):
            self.set_fill_color(*color)
            self.rect(ML, body_start, 2, h, "F")
            self.set_fill_color(*LIGHT)

        # two-column labels
        COL1 = TW / 2 - 3
        COL2 = TW / 2 - 3

        # section label row
        self.set_fill_color(*LGRAY)
        self.rect(ML + 2, self.get_y(), TW - 2, 5.5, "F")
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*NAVY)
        self.set_xy(ML + 5, self.get_y())
        self.cell(COL1, 5.5, "FOCUS AREAS")
        self.set_xy(ML + COL1 + 8, self.get_y() - 5.5)
        self.cell(COL2, 5.5, "KEY DELIVERABLES")
        self.ln(5.5)

        # items row by row (zip in pairs)
        max_rows = max(len(focus_items), len(deliverables))
        for i in range(max_rows):
            fi = focus_items[i] if i < len(focus_items) else ""
            di = deliverables[i] if i < len(deliverables) else ""
            row_y = self.get_y()
            fill = WHITE if i % 2 == 0 else LIGHT
            self.set_fill_color(*fill)
            self.rect(ML + 2, row_y, TW - 2, 5.5, "F")
            # focus cell
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*BLACK)
            self.set_xy(ML + 5, row_y)
            self.cell(COL1, 5.5, fi[:60])
            # deliverable cell
            self.set_xy(ML + COL1 + 8, row_y)
            self.cell(COL2, 5.5, di[:60])
            self.ln(5.5)

        # result bar
        body_end = self.get_y()
        left_stripe(body_end - body_start)
        self.set_fill_color(*color)
        self.rect(ML + 2, self.get_y(), TW - 2, 7, "F")
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*GOLD)
        self.set_xy(ML + 5, self.get_y() + 1)
        self.cell(18, 5, "RESULT:")
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*WHITE)
        self.set_xy(ML + 23, self.get_y() - 5)
        self.multi_cell(TW - 23, 5, result)
        self.ln(3)


# ════════════════════════════════════════════════════════════════════════════
# BUILD
# ════════════════════════════════════════════════════════════════════════════
pdf = PDF()

# ─── COVER ──────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.set_fill_color(*NAVY)
pdf.rect(0, 0, PW, 95, "F")
pdf.set_fill_color(*GOLD)
pdf.rect(0, 93.5, PW, 2, "F")

pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 24)
pdf.set_xy(ML, 22)
pdf.cell(0, 12, "AI-Assisted EDA Pipeline", align="C")
pdf.set_font("Helvetica", "B", 13)
pdf.set_xy(ML, 38)
pdf.cell(0, 8, "GDOT Traffic Dataset -- Subagent Workflow Design", align="C")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(190, 205, 230)
pdf.set_xy(ML, 50)
pdf.cell(0, 6, "How the EDA was decomposed into eight specialized analysis agents", align="C")

stats = [("8", "Specialized\nSubagents"), ("7", "Analysis\nTracks"),
         ("286", "Stations\nAnalyzed"),   ("818K", "Clean Records\nProduced")]
bw, bh, by = 38, 24, 63
for i, (val, lbl) in enumerate(stats):
    bx = ML + i * (bw + 3)
    pdf.set_fill_color(40, 65, 115)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.7)
    pdf.rect(bx, by, bw, bh, "DF")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*GOLD)
    pdf.set_xy(bx, by + 4)
    pdf.cell(bw, 7, val, align="C")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(190, 210, 240)
    pdf.set_xy(bx, by + 13)
    pdf.multi_cell(bw, 4, lbl, align="C")

pdf.set_text_color(*BLACK)
pdf.set_xy(ML, 103)
pdf.set_font("Helvetica", "", 10.5)
pdf.multi_cell(TW, 6,
    "This document describes how the GDOT Traffic Dataset EDA was structured as a "
    "multi-agent AI pipeline. Rather than running a single monolithic analysis, the "
    "project was decomposed into eight specialized subagents -- each with a defined "
    "scope, a set of analytical questions, and concrete deliverables.\n\n"
    "The pipeline was designed so each agent builds on the previous: starting from "
    "raw data inventory, progressing through quality auditing and behavioral profiling, "
    "and culminating in a modeling-ready feature dataset and synthesized EDA report.\n\n"
    "Contents:  (1) Design rationale  (2) Pipeline architecture  "
    "(3) Agent descriptions  (4) Outputs and oversight"
)
pdf.ln(5)
pdf.rule()
pdf.set_font("Helvetica", "I", 9)
pdf.set_text_color(*GRAY)
pdf.cell(0, 5, "Kevin Li  --  GDOT EDA Project  --  2024", align="C")


# ─── PAGE 2: RATIONALE + ARCHITECTURE ───────────────────────────────────────
pdf.add_page()
pdf.section_heading("1.  Why a Multi-Agent Pipeline?")
pdf.body(
    "The GDOT dataset spans three data tiers, 286 stations, and eight years of traffic "
    "records. Decomposing it into eight focused agents ensured each domain was covered "
    "thoroughly and independently."
)

rationale = [
    ("Separation of concerns",  "Each agent owns one question type -- quality, behavior, trends, "
                                 "etc. -- without mixing concerns."),
    ("Parallelism",              "Independent agents (traffic profiling, corridor analysis) can "
                                 "run simultaneously."),
    ("Auditability",             "Every agent saves outputs separately, making any finding "
                                 "traceable back to its source."),
    ("Scalability",              "Scripts run across all 286 stations; adding new years only "
                                 "requires re-running the relevant agent."),
    ("Manager synthesis",        "A final manager agent reads all outputs, resolves contradictions, "
                                 "and produces the unified EDA report."),
]
for label, text in rationale:
    pdf.bullet(label + ": ", text, size=9.5, indent=4, label_w=46)
pdf.ln(2)

pdf.section_heading("2.  Pipeline Architecture")
pdf.body(
    "Agents 1-2 must finish first (trust flags from the quality audit feed downstream). "
    "Agents 3-6 can run in parallel. Agent 7 requires 3-6 to complete. "
    "Agent 8 synthesizes all outputs."
)
pdf.ln(1)

# pipeline boxes -- two rows of 4
AGENTS_FLOW = [
    ("1", "station_inventory",     "Data inventory\n& metadata"),
    ("2", "missingness_quality",   "Missing data\naudit"),
    ("3", "traffic_profile",       "Traffic behavior\nprofiles"),
    ("4", "temporal_trend",        "Trends, AADT\n& holidays"),
    ("5", "corridor_relationship", "Station\ncorrelations"),
    ("6", "anomaly_representativeness", "Anomaly &\ntrust tiers"),
    ("7", "feature_pipeline",      "Feature eng.\n& clean data"),
    ("8", "eda_manager",           "Synthesis &\nmaster report"),
]

COLORS_FLOW = [NAVY, NAVY, ACCENT, ACCENT, TEAL, TEAL, GREEN, GREEN]
bw2, bh2, gap2 = 38, 20, 4

for row in range(2):
    row_y = pdf.get_y()
    row_agents = AGENTS_FLOW[row*4:(row+1)*4]
    row_colors  = COLORS_FLOW[row*4:(row+1)*4]
    for i, ((num, short, desc), col) in enumerate(zip(row_agents, row_colors)):
        bx = ML + i * (bw2 + gap2)
        pdf.set_fill_color(*col)
        pdf.rect(bx, row_y, bw2, bh2, "F")
        # number
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*GOLD)
        pdf.set_xy(bx + 1.5, row_y + 1.5)
        pdf.cell(5, 4, num)
        # name
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(bx + 1.5, row_y + 5.5)
        pdf.multi_cell(bw2 - 2, 3.3, short.replace("_", " "))
        # desc
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(190, 215, 240)
        pdf.set_xy(bx + 1.5, row_y + 13)
        pdf.multi_cell(bw2 - 2, 3, desc)
        # arrow
        if i < 3:
            ax = bx + bw2 + 1
            ay = row_y + bh2 / 2
            pdf.set_draw_color(*GOLD)
            pdf.set_line_width(0.5)
            pdf.line(ax, ay, ax + gap2 - 1, ay)
    pdf.set_y(row_y + bh2 + 2)
    if row == 0:
        # down arrow
        mid_x = ML + 1.5 * (bw2 + gap2) + bw2 / 2
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(0.5)
        pdf.line(mid_x, pdf.get_y(), mid_x, pdf.get_y() + 4)
        pdf.ln(5)

pdf.ln(1)
pdf.callout(
    "Note: Agents 1-2 are sequential prerequisites. Agents 3-6 are parallel. "
    "Agent 7 requires agents 3-6. Agent 8 reads all outputs and is the final step."
)


# ─── PAGES 3-4: AGENT CARDS ─────────────────────────────────────────────────
pdf.add_page()
pdf.section_heading("3.  Agent Descriptions")
pdf.ln(1)

AGENT_DATA = [
    dict(
        number=1, color=NAVY,
        name="station_inventory_agent",
        role="Understand what data exists before any analysis begins",
        focus=[
            "Total station count, station-years, station-months",
            "Functional class distribution (Interstate to Collector)",
            "Urban vs. rural breakdown",
            "Complete vs. incomplete month counts per station",
            "Schema consistency across data tiers and years",
        ],
        deliverables=[
            "Station master table (286 stations)",
            "Completeness table by station-month",
            "Metadata summary and coverage heatmap",
            "Schema / data dictionary audit",
        ],
        result=(
            "286 stations confirmed across 5 functional classes; 8-year coverage verified; "
            "3-tier schema differences documented (COSIT ID format mismatch flagged for downstream handling)."
        ),
    ),
    dict(
        number=2, color=NAVY,
        name="missingness_quality_agent",
        role="Quantify and characterize all data gaps before behavioral analysis",
        focus=[
            "% missing by station, month, hour, day of week",
            "Station x date missingness heatmaps",
            "Run-length distribution of consecutive missing days",
            "Zero-volume and low-coverage interval detection",
            "Outage pattern labeling: random / block / bursty / weekday-heavy",
        ],
        deliverables=[
            "Missingness scorecards per station",
            "Outage pattern taxonomy",
            "Flagged data-quality windows",
            "Cautious MCAR/MAR language enforced throughout",
        ],
        result=(
            "91.6% overall completeness; missingness is structured, not random -- "
            "interstates show higher rates, consistent with methodology differences rather than sensor failure."
        ),
    ),
    dict(
        number=3, color=ACCENT,
        name="traffic_profile_agent",
        role="Establish what normal traffic looks like at each station",
        focus=[
            "Daily volume distributions per station",
            "Hourly volume profiles and AM/PM peak times",
            "Day-of-week and monthly seasonal profiles",
            "Weekday vs. weekend ratio comparisons",
            "Vehicle mix, speed, and class distributions",
        ],
        deliverables=[
            "Station profile plots (hourly, DOW, monthly)",
            "AM/PM peak time summary across all stations",
            "Healthy traffic signature table",
            "Station archetype notes by functional class",
        ],
        result=(
            "Stable AM peak at 7:00, PM peak at 17:00 across all seasons and functional classes. "
            "Predictable weekday/weekend ratio confirmed -- reliable fixed features for AADT models."
        ),
    ),
    dict(
        number=4, color=ACCENT,
        name="temporal_trend_agent",
        role="Understand how traffic evolved over 8 years including COVID effects",
        focus=[
            "Annual AADT trends by station (2017-2024)",
            "Year-over-year monthly volume changes",
            "STL seasonal decomposition (trend + seasonality + residual)",
            "Holiday and long-weekend effect quantification",
            "AM/PM peak hour factor stability across years",
        ],
        deliverables=[
            "AADT trend plots and summary table",
            "Decomposition plots per station",
            "Holiday effect ratios (6 holidays x 5 functional classes)",
            "Long-weekend day-by-day volume ratio chart",
        ],
        result=(
            "COVID caused 8.6% traffic drop in 2020; recovered by 2022. "
            "Independence Day shows largest suppression (~23%). "
            "Holiday correction factors computed for all functional classes."
        ),
    ),
    dict(
        number=5, color=TEAL,
        name="corridor_relationship_agent",
        role="Identify which stations behave similarly for gap-filling imputation",
        focus=[
            "Pairwise Pearson correlation matrices by month",
            "Station-pair daily volume scatter plots",
            "Lead/lag cross-correlation between stations",
            "Distance vs. correlation relationship",
            "Behavioral vs. geographic neighbor comparison",
        ],
        deliverables=[
            "Pairwise correlation matrix (286 x 286)",
            "Behavioral neighbor table per station",
            "27 reference station candidates (r > 0.85)",
            "Corridor relationship memo",
        ],
        result=(
            "27 reference stations confirmed with r > 0.85. Geographic proximity alone is a poor predictor -- "
            "behavioral similarity crosses corridor boundaries in several cases."
        ),
    ),
    dict(
        number=6, color=TEAL,
        name="anomaly_representativeness_agent",
        role="Flag suspicious periods and assign trust tiers to every station-month",
        focus=[
            "Anomaly detection: rolling median + MAD method",
            "Anomaly detection: daily IQR-based thresholds",
            "Sensor-error anomalies vs. real-world events",
            "Representativeness of incomplete station-months",
            "Observed-day sufficiency analysis",
        ],
        deliverables=[
            "Anomaly flags with event attribution",
            "Station trust tiers: TRUSTED / CAUTION / EXCLUDED",
            "Station-month representativeness assessment",
            "Event impact summary (90.5% of anomalies explained)",
        ],
        result=(
            "243 TRUSTED, 36 CAUTION, 7 EXCLUDED. "
            "90.5% of flagged anomalies attributed to known events. "
            "84.9% of stations pass all quality checks."
        ),
    ),
    dict(
        number=7, color=GREEN,
        name="feature_pipeline_agent",
        role="Produce the final modeling-ready dataset with engineered features",
        focus=[
            "Compare 5-min / 15-min / hourly / daily resolutions",
            "Engineer temporal features (DOW, month, peak flags, season)",
            "Create event flags (holiday, construction, long weekend)",
            "Build lag and rolling volume features",
            "Composition features (truck share, heavy vehicle share)",
        ],
        deliverables=[
            "clean_hourly_2024_trusted.csv -- 818,645 records",
            "286-station feature table with 27 predictors",
            "all_events_2024.csv -- event flag database",
            "Feature specification and preprocessing document",
        ],
        result=(
            "Hourly resolution selected for AADT modeling. "
            "818,645 clean records across 243 trusted stations. "
            "27-predictor feature table ready for regression pipeline."
        ),
    ),
    dict(
        number=8, color=GREEN,
        name="eda_manager_agent",
        role="Synthesize all agent outputs into one coherent EDA conclusion",
        focus=[
            "Cross-agent contradiction resolution",
            "Strongest finding identification with evidence",
            "Risk and caveat documentation",
            "Modeling readiness assessment",
            "Trusted and caution station list compilation",
        ],
        deliverables=[
            "Master EDA report (PDF, 14 pages)",
            "Presentation deck (PPTX, 15 slides)",
            "Trusted stations list (243) + caution list (36)",
            "Modeling readiness statement and next-step plan",
        ],
        result=(
            "EDA concluded: data is ready for AADT modeling. Key risks documented: "
            "schema differences across tiers, interstate missingness ambiguity, "
            "5 sparse stations requiring field record investigation."
        ),
    ),
]

for ag in AGENT_DATA:
    pdf.agent_card(
        ag["number"], ag["name"], ag["role"], ag["color"],
        ag["focus"], ag["deliverables"], ag["result"]
    )


# ─── PAGE 5: OUTPUTS + OVERSIGHT ────────────────────────────────────────────
pdf.add_page()

pdf.section_heading("4.  Key Pipeline Outputs")
pdf.body(
    "Together, the eight agents produced the following concrete deliverables "
    "that form the complete EDA record for the GDOT project:"
)
pdf.ln(1)

outputs = [
    ("clean_hourly_2024_trusted.csv",       "818,645 hourly records, 243 trusted stations"),
    ("station_catalog.csv",                 "286-station master table with metadata and trust tier"),
    ("all_events_2024.csv",                 "Holiday, construction, and weather event flag database"),
    ("Feature table (27 predictors)",       "DOW, month, peak flags, rolling volumes, truck share"),
    ("Missingness scorecards",              "Per-station % missing, outage pattern, quality flags"),
    ("Holiday effect ratios",               "6 holidays x 5 functional classes -- correction factors"),
    ("27 reference stations",              "Behavioral neighbors for gap-filling imputation"),
    ("Trust tier assignments",              "243 TRUSTED  /  36 CAUTION  /  7 EXCLUDED"),
    ("Master EDA report (PDF, 14 pages)",   "Full narrative findings with all figures"),
    ("Presentation deck (PPTX, 15 slides)", "Story-arc slides with speaker notes and callouts"),
]
for i, (name, desc) in enumerate(outputs):
    fill = LIGHT if i % 2 == 0 else WHITE
    y0 = pdf.get_y()
    pdf.set_fill_color(*fill)
    pdf.rect(ML, y0, TW, 6.5, "F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(ML, y0, 1.2, 6.5, "F")
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(ML + 4, y0 + 1)
    pdf.cell(76, 4.8, name)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(ML + 82, y0 + 1)
    pdf.multi_cell(TW - 80, 4.8, desc)
    pdf.set_y(y0 + 6.5)

pdf.ln(4)
pdf.section_heading("5.  Human Oversight and Verification")
pdf.body(
    "The subagent pipeline accelerated the analysis but did not replace human judgment. "
    "Every stage involved direct review:"
)
pdf.ln(1)

oversight = [
    ("Code review",         "All agent-produced scripts were read, tested, and run manually."),
    ("Output verification", "Every figure was reviewed -- several required targeted debugging "
                            "(e.g., holiday figures blank due to a COSIT ID format mismatch)."),
    ("Trust decisions",     "Station tier assignments were cross-checked against known events "
                            "and domain knowledge before being accepted."),
    ("Language caution",    "Missingness mechanism language was revised to remain cautious -- "
                            "\"consistent with structured missingness\" not \"MAR\" or \"MCAR\"."),
    ("Presentation edits",  "Slide titles, narrative framing, and speaker notes were all "
                            "edited by the analyst after reviewing each agent draft."),
]
for label, text in oversight:
    pdf.bullet(label + ": ", text, size=9.5, indent=4, label_w=40)
    pdf.ln(0.5)

pdf.ln(3)
pdf.callout(
    "AI agents handled decomposition, code drafting, and output organization. "
    "The analyst handled verification, interpretation, and all final decisions. "
    "The pipeline made it possible to cover 286 stations across 8 years thoroughly -- "
    "work that would have taken significantly longer without structured agent support.",
    bg=LIGHT, bar=NAVY
)

# closing footer bar
pdf.ln(5)
pdf.set_fill_color(*NAVY)
pdf.rect(ML, pdf.get_y(), TW, 12, "F")
pdf.set_fill_color(*GOLD)
pdf.rect(ML, pdf.get_y(), TW, 1.5, "F")
pdf.set_xy(ML, pdf.get_y() + 3.5)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*WHITE)
pdf.cell(0, 5,
    "8 agents  |  286 stations  |  818K records  |  Data ready for AADT modeling",
    align="C")

pdf.output(str(PDF_PATH))
print(f"Saved: {PDF_PATH}  ({PDF_PATH.stat().st_size // 1024} KB,  {pdf.page} pages)")
