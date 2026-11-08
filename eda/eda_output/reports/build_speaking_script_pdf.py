"""
Generates gdot_presentation_speaking_script.pdf — a full written-out speaking script
for all 14 slides of the GDOT EDA presentation.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    KeepTogether, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from pathlib import Path

OUT = Path(__file__).resolve().parent / "gdot_presentation_speaking_script.pdf"

# ── colours ───────────────────────────────────────────────────────────────────
NAVY   = HexColor("#17365D")
GOLD   = HexColor("#C4982A")
LGRAY  = HexColor("#F0F3F8")
DKGRAY = HexColor("#444455")
RED    = HexColor("#C03030")

# ── styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "DocTitle",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=22,
    textColor=NAVY,
    spaceAfter=6,
    leading=28,
    alignment=TA_CENTER,
)
SUBTITLE_STYLE = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=11,
    textColor=DKGRAY,
    spaceAfter=4,
    leading=15,
    alignment=TA_CENTER,
)
SLIDE_HEADER_STYLE = ParagraphStyle(
    "SlideHeader",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=14,
    textColor=white,
    leading=18,
    leftIndent=10,
    rightIndent=10,
    spaceBefore=0,
    spaceAfter=0,
)
SLIDE_TITLE_STYLE = ParagraphStyle(
    "SlideTitle",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=12,
    textColor=NAVY,
    spaceBefore=10,
    spaceAfter=4,
    leading=16,
)
META_STYLE = ParagraphStyle(
    "Meta",
    parent=styles["Normal"],
    fontName="Helvetica-Oblique",
    fontSize=9,
    textColor=DKGRAY,
    spaceAfter=8,
    leading=12,
)
BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10.5,
    textColor=black,
    leading=16,
    spaceAfter=9,
    alignment=TA_JUSTIFY,
)
QUOTE_STYLE = ParagraphStyle(
    "Quote",
    parent=styles["Normal"],
    fontName="Helvetica-Oblique",
    fontSize=10.5,
    textColor=NAVY,
    leading=16,
    leftIndent=24,
    rightIndent=12,
    spaceAfter=9,
    alignment=TA_JUSTIFY,
)
SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    textColor=NAVY,
    spaceBefore=10,
    spaceAfter=4,
    leading=14,
)
TIP_STYLE = ParagraphStyle(
    "Tip",
    parent=styles["Normal"],
    fontName="Helvetica-Oblique",
    fontSize=9.5,
    textColor=DKGRAY,
    leading=13,
    leftIndent=18,
    spaceAfter=8,
)

def slide_header_block(num, title, timing):
    """Navy banner row with slide number, title, and timing."""
    data = [[
        Paragraph(f"Slide {num}", ParagraphStyle("n", fontName="Helvetica-Bold",
                  fontSize=11, textColor=white, alignment=TA_CENTER)),
        Paragraph(title, SLIDE_HEADER_STYLE),
        Paragraph(timing, ParagraphStyle("t", fontName="Helvetica",
                  fontSize=9, textColor=HexColor("#DCE6F2"), alignment=TA_CENTER)),
    ]]
    t = Table(data, colWidths=[0.65*inch, 5.40*inch, 1.05*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LINEAFTER", (0, 0), (0, 0), 0.5, GOLD),
    ]))
    return t

def gold_bar():
    return HRFlowable(width="100%", thickness=2, color=GOLD,
                      spaceAfter=10, spaceBefore=2)

def body(text):
    return Paragraph(text, BODY_STYLE)

def quote(text):
    return Paragraph(f"“{text}”", QUOTE_STYLE)

def section(text):
    return Paragraph(text, SECTION_STYLE)

def tip(text):
    return Paragraph(f"[{text}]", TIP_STYLE)

def sp(h=6):
    return Spacer(1, h)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDES — full speaking text
# ═══════════════════════════════════════════════════════════════════════════════

slides = []

# ── SLIDE 1 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=1,
    title="GDOT Traffic Dataset EDA — Title Slide",
    timing="~30 sec",
    content=[
        tip("Stand at the front, let the title slide settle, then begin."),
        body("Good morning / afternoon. This presentation covers an eight-year exploratory data analysis "
             "of Georgia DOT's statewide traffic monitoring network — 286 sensor stations collecting "
             "five-minute interval counts from 2017 through 2024."),
        body("Before we get into the findings, I want to surface the research question that runs through "
             "everything you are about to see: how many days of data does a partially-observed month "
             "need before we can call it statistically representative of normal traffic?"),
        body("The short answer we will work toward is fourteen to eighteen days. That is meaningfully "
             "less than the twenty-six days required by the current standard operating procedure — and "
             "the gap has real consequences for how many months we can or cannot use in downstream "
             "analysis."),
        tip("Pause briefly after the key finding. Then transition:"),
        body("Let us start by understanding exactly what data we are working with."),
    ]
))

# ── SLIDE 2 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=2,
    title="The Data We Have: 8 Years Across 286 Stations",
    timing="~1 min",
    content=[
        tip("Walk left to right across the five large stat boxes."),
        body("The dataset spans 286 stations, eight full calendar years from 2017 through 2024, "
             "and 91.6 percent of all station-months have complete data. Out of those 286 stations, "
             "243 passed all quality checks and were designated TRUSTED. And for the year 2024 — "
             "our most complete and recent year — we produced 818,000 clean hourly records."),
        tip("Point to the heatmap, Figure 3."),
        body("This heatmap is a bird's-eye view of the entire dataset. Each row is one station, "
             "each column is one calendar month. Green means the station-month is complete. "
             "Yellow and orange indicate partial data. Red and white are gaps. What you should "
             "notice is that the vast majority of the grid is green — the gaps are the exception, "
             "not the rule."),
        tip("Point to Figures 1 and 2, the bar charts on the right."),
        body("Looking at the fleet composition: about 42 percent of stations are on interstates "
             "and freeways, and roughly 70 percent are in urban areas. That mix matters later "
             "when we see that interstate stations show disproportionately high missingness — "
             "and why that may be misleading."),
        tip("Transition:"),
        body("So the data is largely complete. But the 8.4 percent that is missing is not "
             "randomly distributed — and that matters a great deal."),
    ]
))

# ── SLIDE 3 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=3,
    title="91.6% Complete — But the Missing 8.4% Has a Pattern",
    timing="~2 min",
    content=[
        body("91.6 percent complete sounds reassuring. But the critical question is not just "
             "how much data is missing — it is whether the missing data is random or structured. "
             "If it is random, simple imputation methods work. If it is structured, they do not."),
        tip("Walk through the five stat boxes."),
        body("73.4 percent of stations are what we call always-on — they rarely miss a reading. "
             "Only 1.8 percent are chronically sparse, meaning they have persistent, long-running "
             "gaps. And across the dataset there are 226 distinct outage runs — but most of "
             "those runs are short."),
        tip("Move to the year-by-year bullets on the right."),
        body("Looking at the annual pattern: 2017 had a 13.6 percent missingness rate. "
             "That is not a data quality failure — it is a deployment artifact. Not all 286 "
             "stations came online on January 1st, 2017. The gaps at the start of the period "
             "simply reflect a network that was still being built out."),
        body("Then in 2022 and 2023, the rate jumped back to around 12 percent. This coincided "
             "with GDOT's transition to a new five-minute data collection system. Sensors that "
             "were mid-upgrade show gaps in the record. By 2024 the rate is recovering — down "
             "to 7.8 percent — but it has not yet returned to the pre-transition baseline."),
        tip("Point to the heatmap, Figure 5."),
        body("This heatmap is the key visual. If missingness were completely random — the MCAR "
             "case in the statistical literature — you would see an even, uniform speckle across "
             "the entire grid. What you actually see is something very different: specific rows "
             "going dark, meaning specific stations losing data simultaneously, and specific time "
             "windows lighting up across many stations at once. That is a structural pattern. "
             "It is not random noise."),
        body("The modeling implication is direct: simple mean-fill imputation will not work here "
             "because the gaps are not scattered uniformly. A method that uses behavioral neighbors "
             "— stations with similar traffic profiles on the same corridor — is the appropriate "
             "response."),
        tip("Transition:"),
        body("One road type stands out as having unusually high missingness. Before we treat "
             "that as a data problem, let us look more carefully at what is actually happening."),
    ]
))

# ── SLIDE 4 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=4,
    title="The Interstate 'Missingness' May Be a Counting Artifact",
    timing="~1.5 min",
    content=[
        body("Interstates show a 13.5 percent missingness rate. Freeways are even higher at "
             "14.6 percent. Compare that to arterials at 4.8 percent and collectors at 3.2 percent, "
             "and it looks like we have a serious reliability problem on our highest-volume roads. "
             "But this finding deserves scrutiny before we act on it."),
        tip("Point to the WHY box in the center column."),
        body("Multi-lane sensors generate more expected data intervals per collection window than "
             "a single-lane detector. A six-lane interstate produces six lane readings every five "
             "minutes. GDOT's completeness check requires that 80 percent of those expected "
             "readings be present. On a single-lane road, missing one reading in five barely "
             "moves the needle. On a six-lane interstate, the same physical gap hits the "
             "completeness calculation much harder. So the elevated missingness rate on FC1 and "
             "FC2 may reflect the counting methodology — not worse sensor performance or worse "
             "data quality."),
        tip("Point to the run-length inset."),
        body("When outages do occur, 52 percent of them last exactly one month. Those are "
             "almost certainly routine maintenance events — a sensor goes offline, gets serviced, "
             "comes back. The other 32 percent that last longer than six months are a different "
             "story — those likely represent full sensor replacements or infrastructure outages, "
             "and they need a different response."),
        body("The research finding at the bottom of this slide is: do not exclude FC1 and FC2 "
             "stations based on missingness rate alone. The proper step is to validate whether "
             "the 80 percent completeness threshold is fair to multi-lane sensors before "
             "making any exclusion decisions. Interstate data may be more reliable than its "
             "missingness rate suggests."),
        tip("Transition:"),
        body("This brings us to the central research question: for any partially-observed month, "
             "across any missingness type, how many observed days do we actually need?"),
    ]
))

# ── SLIDE 5 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=5,
    title="The 26-Day SOP Fits No Station Perfectly — k* Depends on Traffic Volume",
    timing="~2.5 min — most important slide",
    content=[
        body("This slide connects the EDA directly to the research paper's central result."),
        body("The GDoT paper ran a network-wide simulation across 84 stations in April 2024. "
             "The question it asked was simple: for a partial month — a month where some days "
             "are missing — how many observed days do you actually need before you can certify "
             "that month as statistically representative of normal traffic? That minimum number "
             "is called k-star. The answer is not a single number. It depends primarily on "
             "how much traffic the station carries."),
        tip("Point to the three-row table on the left."),
        body("For high-volume stations — interstates and freeways carrying more than 15,000 "
             "vehicles per day — k-star is 14 days. These stations have high, stable traffic "
             "volumes that are easy to predict from partial data. A corridor neighbor can fill "
             "in the gap reliably. 14 days of observation is enough for a conformal interval "
             "to meet the sufficiency threshold. These stations make up 42 percent of the network."),
        body("For medium-volume stations — principal arterials and minor arterials in the "
             "5,000 to 15,000 range — k-star is 18 days. The prediction is a bit harder "
             "because these roads mix commuter and through traffic in patterns that are "
             "slightly less consistent. You need a few more days to pin down a reliable "
             "estimate. This tier covers roughly 50 percent of the network."),
        body("For low-volume stations — major collectors below 5,000 vehicles per day — "
             "k-star rises to 24 days. These roads have the most variable day-to-day "
             "profiles, smaller reference pools, and wider conformal intervals. The paper "
             "also found that some low-volume stations never reach the sufficiency threshold "
             "even at 28 observed days."),
        tip("Point to the 'vs. 26-day SOP' column on the right of the table."),
        body("Now compare those thresholds against the current 26-day standard operating "
             "procedure. For high-volume stations, the SOP is over-restrictive by 12 days — "
             "it is discarding months the paper says are certifiable. For medium-volume "
             "stations, it is over-restrictive by about 8 days. For low-volume collectors, "
             "the SOP is roughly appropriate — and in some cases even 26 days is not enough."),
        body("So the problem with the current rule is not simply that it is too strict. "
             "It is that it applies one number to three fundamentally different situations. "
             "It over-restricts the majority of the network and cannot help the stations "
             "that genuinely need more data."),
        tip("Point to the key finding box."),
        body("The paper's headline finding is this: traffic volume is the primary driver of "
             "k-star, not the type of missingness. Whether gaps are random, block-shaped, or "
             "bursty matters less than how predictable the station's traffic profile is — "
             "and predictability comes from volume."),
        tip("Point to the sufficiency bands figure on the right, Figure 10."),
        body("This chart shows our EDA data plotted against a k-star of 18 days, which is "
             "the midpoint threshold appropriate for medium-volume stations. 96.8 percent of "
             "station-months already clear 26 days and pass the current SOP. The one percent "
             "in the middle band — about 213 station-months between 18 and 25 days — are "
             "recoverable for medium-to-high-volume stations under the paper's framework. "
             "The 2.2 percent below 18 days are genuinely insufficient regardless of method."),
        tip("Point to the Phase 2 box."),
        body("Phase 2 will apply volume-tier-aware conformal thresholds station by station, "
             "using the 27 reference station candidates the EDA identified as the comparison pool."),
        body("The bottom line: the 26-day rule is the wrong instrument because it is one "
             "size that fits no station well. What the paper points toward is a threshold "
             "that adapts to station volume — strict enough for collectors, lenient enough "
             "to stop wasting certifiable months on high-volume interstates."),
        tip("Transition:"),
        body("Before we can certify any of those months, we need confidence that the "
             "underlying data is trustworthy. So let us answer that question directly."),
    ]
))

# ── SLIDE 6 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=6,
    title="Can We Trust This Data? Mostly, Yes.",
    timing="~1.5 min",
    content=[
        body("The short answer is yes — with a small but important caveat. 84.9 percent of "
             "stations pass all quality checks cleanly."),
        tip("Walk through the anomaly detection results on the left."),
        body("We ran anomaly detection on a 58-station sample using a combination of rolling "
             "median absolute deviation and interquartile range based flagging — both robust "
             "to the kind of heavy-tailed traffic distributions we see here. That process "
             "found 391 anomaly-days across those 58 stations. Of those, 354 — or 90.5 percent "
             "— are directly explained by entries in the GDOT event database. Construction "
             "closures, signal failures, major crashes. Only 37 anomaly-days are unexplained."),
        tip("Walk through the trust tier table — and explain what Trusted actually means."),
        body("Before reading the numbers, it is worth being clear about what Trusted means, "
             "because it is not a GDOT-designated label. It is a quality classification we "
             "defined and applied ourselves. The process had three steps. First, each "
             "station-month was scored individually: a month was marked clean if its coverage "
             "exceeded 85 percent and it contained no anomaly days that could not be explained "
             "by a known event in the GDOT database. Second, each station was given an overall "
             "rating based on what fraction of its months were clean — stations where at least "
             "80 percent of months passed were rated HIGH. Third, a station only made it onto "
             "the final Trusted list if it was rated HIGH, had data from at least two "
             "independent sources, and had at least eight clean months on record. Everything "
             "else became CAUTION or EXCLUDED."),
        body("Applying that classification to all 286 stations gave us three tiers. TRUSTED "
             "covers 243 stations and 96.9 percent of all 20,600 station-months — these are "
             "the primary modeling population. CAUTION covers 36 stations — useful for "
             "sensitivity tests but not for primary conclusions. EXCLUDED covers just 7 "
             "stations with persistent quality issues that need manual investigation."),
        tip("Point to the 'What this means' box."),
        body("In practical terms: train models on the 243 TRUSTED stations. Use the 36 "
             "CAUTION stations to check whether results are sensitive to borderline data. "
             "Flag the 7 EXCLUDED stations for the GDOT data team. The overall picture "
             "is one of a well-functioning sensor network with isolated, explicable problems."),
        tip("Transition:"),
        body("Now that we know the data is sound, let us look at what normal traffic "
             "actually looks like across this network."),
    ]
))

# ── SLIDE 7 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=7,
    title="Traffic Is Predictable: Same Peaks, Every Day, Every Season",
    timing="~1.5 min",
    content=[
        body("One of the most reassuring findings from the EDA is how consistent traffic "
             "behavior is across the network. Once you understand the basic daily rhythm, "
             "almost everything else makes sense."),
        tip("Walk through the summary stat table on the left."),
        body("The median daily volume across the 100-station sample is about 22,800 vehicles "
             "per day. The mean is 45,200 — that gap tells you the distribution is strongly "
             "right-skewed, because freeway and interstate stations pull the average up. "
             "FC2 freeways come in around 110,000 vehicles per day. FC1 interstates around "
             "52,000. FC3 other principal arterials around 19,000."),
        tip("Point to the hourly profile chart, Figure 13."),
        body("The hourly volume chart shows the classic double-hump profile: a morning peak "
             "at 7 AM and an afternoon peak at 5 PM. What makes this statistically useful "
             "is that these two peaks hold across every road type, every season, and every "
             "year in the dataset. Summer versus winter, urban versus rural — same two peaks, "
             "same relative heights. That stability is the empirical foundation for using "
             "reference months as comparators."),
        tip("Point to the weekday-to-weekend ratio note."),
        body("The overall weekday-to-weekend ratio is 1.25 — meaning weekdays carry about "
             "25 percent more traffic than weekends on average. But the breakdown by functional "
             "class is more informative. Interstates show a ratio of only 1.08 — freight "
             "and through-travelers keep them nearly uniform across all seven days. Arterials "
             "and collectors show ratios of 1.35 to 1.44 — those are strongly commuter-oriented "
             "roads where weekday peaks are much more pronounced."),
        body("The stability of these patterns is what makes the conformal testing approach "
             "viable in the first place. If traffic were chaotic or unpredictable from one "
             "month to the next, comparing a partial month to a reference pool would be "
             "meaningless. The consistent AM-PM structure means reference months are "
             "genuinely meaningful comparators."),
        tip("Transition:"),
        body("Now let us look at how these traffic volumes have changed across the eight "
             "years of the study period."),
    ]
))

# ── SLIDE 8 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=8,
    title="COVID Dropped Traffic 8.6%. It Came Back by 2022.",
    timing="~1.5 min",
    content=[
        body("Two distinct forces shape the long-run trajectory of traffic in this dataset: "
             "a one-time external shock from COVID-19, and a recurring seasonal cycle that "
             "has been present throughout. Any model that reads this data needs to account "
             "for both — and they require different treatments."),
        tip("Point to the AADT trend chart, Figure 16."),
        body("The AADT proxy trend tracks the June mean daily volume for a 30-station "
             "sample from 2018 to 2023. June is used because it is the least seasonally "
             "biased month of the year and avoids the need for a full calendar year of data "
             "to compute a reliable annual average. The COVID-19 drop is clearly visible: "
             "a median decline of 8.6 percent from 2019 to 2020 across all functional classes. "
             "By 2021 and 2022, most stations had returned to near-2019 volumes. Freeways "
             "recovered fastest — likely because freight traffic, which never stopped, "
             "dominated those roads. Major collectors recovered slowest."),
        tip("Point to the seasonal index chart, Figure 17."),
        body("The seasonal cycle is a roughly plus-or-minus 10 percent annual swing around "
             "the baseline. Traffic peaks in October — the seasonal index for October is "
             "1.036, meaning October is about 3.6 percent above the annual mean. The trough "
             "is January, at a seasonal index of 0.928 — about 7.2 percent below the annual "
             "mean. That is a fairly tight seasonal band. Rural FC4 and FC5 stations show "
             "stronger seasonal variation than interstates, which are moderated by the "
             "consistent flow of freight. Peak hours — 7 AM and 5 PM — are stable across "
             "all four seasons even as overall volume shifts."),
        body("The distinction matters for modeling: the COVID dip is a one-time, resolved "
             "event. The seasonal cycle repeats every year and will continue to repeat. "
             "Treating them as the same kind of variation would lead to poor predictions. "
             "The COVID period — 2020 through early 2022 — should be treated as a structural "
             "break in any long-run AADT analysis."),
        tip("Transition:"),
        body("There is one type of temporal variation we attempted to quantify but could "
             "not fully close out — holiday effects."),
    ]
))

# ── SLIDE 9 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=9,
    title="Holiday Effects Are a Bias Risk — First Fix the ID Join",
    timing="~1 min",
    content=[
        tip("Be transparent and direct about what this slide is showing."),
        body("This is an honest slide about a known limitation. We attempted to quantify "
             "how holidays and long weekends affect daily traffic volumes — because those "
             "effects can meaningfully bias monthly AADT estimates, especially for stations "
             "near major destinations or travel corridors. The analysis could not produce "
             "usable correction factors."),
        tip("Point to Figures 18 and 19."),
        body("Both diagnostic charts — the holiday-effect check and the long-weekend check "
             "— show empty or not-a-number output. This is not because holidays do not "
             "affect traffic. It is because the GDOT event database uses a station identifier "
             "format that does not match the station IDs in the 2024 COSIT traffic files. "
             "The join between those two tables fails silently — the query runs without "
             "error, but returns no matched records, so every ratio is undefined."),
        body("The consequence is that holiday correction factors remain unquantified. "
             "A station near a major destination — an airport, a stadium, an outlet mall "
             "— may show monthly AADT inflation on holiday weekends that goes uncorrected. "
             "This is listed as one of the three primary blockers before full modeling "
             "can begin."),
        body("The fix is technically straightforward: rebuild the COSIT lookup table with "
             "the correct station ID crosswalk and re-run the holiday analysis. That work "
             "is scoped but not yet executed."),
        tip("Transition:"),
        body("Moving from individual station behavior to how stations relate to each other "
             "across the network."),
    ]
))

# ── SLIDE 10 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=10,
    title="Nearby Stations Tend to Behave Alike",
    timing="~1.5 min",
    content=[
        body("The hypothesis going into the corridor relationship analysis was that stations "
             "on the same road — close to each other spatially — should show similar traffic "
             "profiles. If that is true, a station with a data gap can be compared to its "
             "corridor neighbors to assess whether its partial months are representative. "
             "The data confirms the hypothesis."),
        tip("Walk through the correlation statistics."),
        body("We computed pairwise Pearson correlations for the top 80 most complete 2024 "
             "stations, requiring at least 180 overlapping days per pair. That produced "
             "2,848 valid station pairs. The mean correlation across all pairs is 0.57, "
             "and the median is 0.64. 411 pairs — about 14 percent of all pairs — cleared "
             "the high-correlation bar of 0.85. These are stations whose daily volumes "
             "rise and fall almost in lockstep."),
        tip("Point to the cluster and reference candidate bullets."),
        body("From that correlation structure, we identified seven multi-station corridor "
             "clusters — groups of stations that all behave similarly because they share "
             "the same road and the same traffic demand. We also found 211 behavioral "
             "neighbor pairs within 50 kilometers where the correlation exceeds 0.70. "
             "And 27 individual stations passed all five quality criteria to be designated "
             "reference station candidates — meaning they are complete, stable, well-connected, "
             "and suitable as donor stations for gap-filling."),
        body("The top reference candidate is station 089-3323 in DeKalb County — an "
             "interstate station with 10 behavioral neighbors. That density of corridor "
             "connections makes it an exceptionally strong anchor for the Phase 2 "
             "conformal testing pool."),
        tip("Acknowledge the limitation."),
        body("One important caveat: this analysis covers only the top 80 stations by "
             "completeness. Approximately 150 additional eligible stations have not yet "
             "been assessed. The 27 reference candidates are a strong starting point "
             "for Phase 2, but they are not a final or exhaustive list."),
        tip("Transition:"),
        body("Let me now summarize what the full EDA delivered as tangible outputs."),
    ]
))

# ── SLIDE 11 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=11,
    title="What the EDA Produced: A Clean, Characterized Dataset",
    timing="~1.5 min",
    content=[
        tip("Frame this as the 'what we built' slide — concrete deliverables."),
        body("The exploratory data analysis did not just produce charts and summaries. "
             "It produced four specific datasets and reference files that Phase 2 will "
             "consume directly."),
        tip("Walk through the clean hourly 2024 dataset."),
        body("The primary output is 818,645 clean hourly records covering 99 trusted "
             "stations for the full calendar year 2024. Mean hourly coverage is 100 "
             "percent at the threshold we set. 1.7 percent of hours required imputation "
             "— they are flagged in the dataset but not removed, so downstream analysts "
             "can choose how to handle them. The median hourly volume is 580 vehicles "
             "per hour, with a maximum of nearly 18,000 on the busiest freeway segments."),
        tip("Walk through the station feature table."),
        body("The second major output is a 286-station, 27-feature table covering the "
             "entire network — not just the 99 stations in the hourly subset. This includes "
             "AADT proxy values, seasonal amplitude estimates per station, functional class, "
             "urban and rural classification, and a recommended aggregation level. For "
             "almost all stations, the recommended resolution is hourly — it preserves "
             "the AM and PM peak structure while filtering out sub-interval noise."),
        tip("Walk through the four output files."),
        body("The four key files are: station_feature_table.csv with 286 stations and 27 "
             "modeling features; clean_hourly_2024_trusted.csv with 818,000 records across "
             "99 stations and 26 columns; reference_station_candidates.csv with the 27 "
             "top gap-filling donor stations; and trusted_station_list.csv with the full "
             "243-station TRUSTED designation list. One file is still pending: holiday "
             "and event correction ratios, which remain blocked by the COSIT ID mismatch."),
        tip("Transition:"),
        body("To produce all of this across 286 stations and eight years of data efficiently, "
             "we used an AI-assisted subagent pipeline. Let me explain briefly how that worked."),
    ]
))

# ── SLIDE 12 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=12,
    title="AI-Assisted Subagent Pipeline Design",
    timing="~1 min",
    content=[
        body("To cover the full scope of the EDA — 286 stations, eight years, seven "
             "analytical dimensions — we decomposed the work into eight specialized "
             "subagents, each responsible for one clearly defined analysis track. "
             "All subagent outputs were human-reviewed and validated before being "
             "accepted into the final results."),
        tip("Walk through the eight agents in pipeline order."),
        body("Station inventory counted and catalogued all 286 stations, audited the "
             "schema across the three data tiers, and flagged the COSIT ID format mismatch "
             "early — before it caused problems downstream. Missingness quality computed "
             "gap statistics at the station, hour, and day-of-week level, labeled outage "
             "patterns, and confirmed the 91.6 percent overall completeness figure. "
             "Traffic profile built the hourly, day-of-week, and monthly volume charts "
             "that confirmed the 7 AM and 5 PM peaks as stable across all seasons. "
             "Temporal trend tracked the AADT proxy trends and seasonality curves, "
             "documenting the 8.6 percent COVID drop in 2020 and the recovery by 2022. "
             "Corridor relationship ran the pairwise correlations and identified the "
             "27 reference station candidates. Anomaly representativeness applied rolling "
             "MAD and IQR anomaly detection and assigned the TRUSTED, CAUTION, and EXCLUDED "
             "designations. Feature pipeline produced the 818,000 clean hourly records "
             "and the 286-station feature table. And the EDA manager synthesized all "
             "eight outputs into the master summary, the roadmap, and this presentation."),
        tip("Point to the stat row at the bottom."),
        body("The aggregate results: 8 agents, 286 stations, 818,000 clean records, "
             "243 trusted stations, and 27 reference candidates — all produced in a "
             "single coordinated analysis cycle."),
        tip("Transition:"),
        body("Let me close with the six key takeaways from everything we have covered."),
    ]
))

# ── SLIDE 13 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=13,
    title="Key Takeaways",
    timing="~2 min",
    content=[
        body("Six findings, organized from the most foundational to the most actionable."),
        section("1.  The Data Is Trustworthy"),
        body("84.9 percent of stations pass all quality checks. 96.9 percent of the 20,600 "
             "station-months assessed are designated TRUSTED. Only 7 stations — 2.5 percent "
             "of the network — are excluded. This is a strong empirical foundation for "
             "Phase 2 modeling."),
        section("2.  Missingness Is Structured, Not Random"),
        body("91.6 percent of expected records are present. The gaps cluster tightly around "
             "known operational events — the 2017 network startup and the 2022 to 2023 "
             "pipeline transition — not as random sensor noise scattered uniformly across "
             "time. Behavioral-neighbor gap-filling using corridor donors is the correct "
             "methodological response."),
        section("3.  Traffic Patterns Are Stable and Interpretable"),
        body("The AM peak sits at 7 AM and the PM peak at 5 PM across every road type and "
             "every season in the dataset. COVID-19 caused a temporary 8.6 percent drop "
             "in 2020, which fully resolved by 2022. Holiday and long-weekend correction "
             "factors are not yet quantified — that is an open gap."),
        section("4.  k* Depends on Traffic Volume — the 26-Day SOP Is the Wrong Instrument"),
        body("The GDoT paper's network-wide analysis of 84 stations found that k-star — "
             "the minimum days needed to certify a partial month — ranges from 14 days for "
             "high-volume interstates to 24 days for low-volume collectors. The 26-day SOP "
             "over-restricts the 42 percent of stations that are high-volume interstates and "
             "freeways, while being approximately right for collectors. About 213 certifiable "
             "station-months sit in the recoverable band that the current rule discards."),
        section("5.  Corridor Neighbors Support Gap-Filling"),
        body("The top-80 correlation analysis found 211 behavioral-neighbor pairs and "
             "27 reference station candidates meeting all quality criteria. Stations on "
             "the same corridor rise and fall in near-lockstep — making corridor donors "
             "a far stronger gap-filling starting point than fleet-wide or functional "
             "class averages."),
        section("6.  Modeling Is Close, With Clear Remaining Blockers"),
        body("The 818,000 hourly records currently cover 99 trusted stations — a useful "
             "subset but not the full network. Three blockers need to be resolved before "
             "full-scale modeling: remove the 100-station processing cap that limited the "
             "hourly pipeline, fix the holiday COSIT ID matching, and expand the corridor "
             "relationship analysis to all eligible stations beyond the top 80."),
        tip("Close with an invitation:"),
        body("I am happy to go deeper on any of these. The volume-tier k-star analysis on "
             "slide 5 is the most directly research-relevant finding — particularly the "
             "implication that the 26-day SOP needs to be disaggregated by station type. "
             "Slide 14 raises two open methodological questions from reading the GDoT paper itself."),
    ]
))

# ── SLIDE 14 ──────────────────────────────────────────────────────────────────
slides.append(dict(
    num=14,
    title="Research Questions from Reading the GDoT Report",
    timing="~2 min",
    content=[
        tip("Signal the tonal shift: this is not EDA findings, it is open research questions."),
        body("The previous 13 slides are findings — things we measured and confirmed from "
             "the data. This last slide is different in character. These are questions and "
             "ideas that came up while reading the GDoT paper itself — things worth "
             "putting on the table for Phase 2 design decisions."),
        section("Question 3 — Weighted Conformal Prediction"),
        body("The current conformal testing method accepts reference months that meet a "
             "Pearson correlation threshold and then treats all accepted months with equal "
             "weight in the test statistic. But not all reference months are equally "
             "similar to the target month. A reference month with a correlation of 0.98 "
             "should intuitively contribute more information than one with a correlation "
             "of 0.72 — yet the current method gives them identical influence."),
        body("The proposed improvement is to weight each reference month by its similarity "
             "to the target, using the formula: w-sub-i equals the exponential of negative "
             "lambda times the quantity one minus r-sub-i, where r-sub-i is the Pearson "
             "correlation between reference month i and the target month. This is a "
             "soft-weighting scheme: months with correlation close to 1.0 get weight "
             "close to 1.0; months with low correlation get weight close to zero. Lambda "
             "controls how aggressively the weighting penalizes weaker matches."),
        body("The practical motivation is in the red box on the left: only 84 of the 185 "
             "eligible stations passed the pool-size requirement under the current binary "
             "threshold approach. The 101 stations that failed were predominantly "
             "low-volume rural stations whose traffic profiles were too variable to "
             "accumulate enough high-correlation reference months. A weighted scheme "
             "might allow those stations to use a larger pool of lower-correlation "
             "months while still giving the strongest matches the most influence — "
             "potentially certifying more rural station-months without formally relaxing "
             "the exchangeability guarantee that conformal testing relies on."),
        section("Question 4 — Reference Pool Sensitivity"),
        body("The second question is about how sensitive the method is to the construction "
             "of the reference pool itself. Right now the pool is built by applying a fixed "
             "Pearson correlation cutoff: above it, you are in; below it, you are out. "
             "But the question is how much that threshold matters for the validity "
             "of the certification."),
        body("There is a genuine trade-off. Relax the threshold and you get more reference "
             "months — which helps rural stations with small pools — but you weaken the "
             "exchangeability assumption that underlies the conformal guarantee. Tighten "
             "the threshold and the theoretical guarantee gets stronger — but you shrink "
             "the pool further, which is already the binding constraint for rural stations."),
        body("The follow-up question from the reading is: for example, if we relax the "
             "correlation threshold we get more reference months, but maybe weaker "
             "exchangeability. How should we balance reference pool size versus "
             "similarity quality? Is there a principled criterion — analogous to an "
             "information criterion in model selection — that could set the threshold "
             "adaptively based on the data available for each station?"),
        tip("Point to the insight box at the bottom right."),
        body("The potential direction that combines both ideas: a weighted reference pool "
             "whose effective size adapts based on the correlation drop-off, rather than "
             "a hard binary cutoff. Instead of asking 'is this month in or out,' the "
             "question becomes 'how much should this month count' — and the answer is "
             "determined smoothly by the correlation. That framing may resolve the "
             "pool-size problem for rural stations without requiring a formal relaxation "
             "of the exchangeability condition."),
        tip("Close the presentation:"),
        body("These two questions are where the EDA findings connect directly to the "
             "open methodological frontier of the paper. They are worth discussing as "
             "Phase 2 gets underway. Thank you."),
    ]
))


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD PDF
# ═══════════════════════════════════════════════════════════════════════════════

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=0.85 * inch,
    rightMargin=0.85 * inch,
    topMargin=0.85 * inch,
    bottomMargin=0.85 * inch,
    title="GDOT EDA Presentation Speaking Script",
    author="Kevin Li",
)

story = []

# ── cover page ─────────────────────────────────────────────────────────────────
story.append(Spacer(1, 0.8 * inch))
story.append(Paragraph("GDOT Traffic Dataset EDA", TITLE_STYLE))
story.append(Spacer(1, 6))
story.append(Paragraph("Presentation Speaking Script", TITLE_STYLE))
story.append(Spacer(1, 14))
story.append(HRFlowable(width="60%", thickness=2, color=GOLD,
                         hAlign="CENTER", spaceAfter=14))
story.append(Paragraph("2017–2024  |  286 Stations  |  Georgia Department of Transportation",
                        SUBTITLE_STYLE))
story.append(Spacer(1, 6))
story.append(Paragraph("Full written-out speaking paragraphs for all 14 slides",
                        SUBTITLE_STYLE))
story.append(Spacer(1, 6))
story.append(Paragraph("Estimated total presentation time: 20–25 minutes",
                        SUBTITLE_STYLE))
story.append(Spacer(1, 0.5 * inch))

# How to use box
how_data = [[
    Paragraph(
        "<b>How to use this script</b><br/>"
        "Each slide section begins with a navy header showing the slide number, title, and suggested timing. "
        "Text in <i>[ square brackets and italics ]</i> are stage directions — notes about what to point to or "
        "when to pause. Everything else is meant to be spoken, in a natural conversational tone. "
        "You do not need to read verbatim — treat the paragraphs as a complete guide that you can adapt "
        "as the presentation flows.",
        ParagraphStyle("how", fontName="Helvetica", fontSize=9.5, textColor=NAVY,
                       leading=14, leftIndent=0)
    )
]]
how_table = Table(how_data, colWidths=[6.3 * inch])
how_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), LGRAY),
    ("TOPPADDING",    (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ("LEFTPADDING",   (0, 0), (-1, -1), 14),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ("LINEAFTER",     (0, 0), (0, 0), 3, NAVY),
]))
story.append(how_table)
story.append(Spacer(1, 0.3 * inch))

# ── slides ─────────────────────────────────────────────────────────────────────
for sl in slides:
    block = []
    block.append(slide_header_block(sl["num"], sl["title"], sl["timing"]))
    block.append(gold_bar())
    for item in sl["content"]:
        block.append(item)
    block.append(Spacer(1, 20))
    story.append(KeepTogether(block[:4]))   # keep header + first paragraph together
    for item in block[4:]:
        story.append(item)

doc.build(story)
print(f"Saved: {OUT}")
print(f"Total slides covered: {len(slides)}")
