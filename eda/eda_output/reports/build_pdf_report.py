"""
Build GDOT EDA Final PDF Report (A4 landscape, 14 slides).
"""
from fpdf import FPDF
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
OUT_PDF = BASE / "eda_output/reports/gdot_eda_final_report.pdf"

# ── figure paths ──────────────────────────────────────────────────────────
INV  = BASE / "eda_output/inventory"
MISS = BASE / "eda_output/missingness"
PROF = BASE / "eda_output/profiles"
TREN = BASE / "eda_output/trends"
CORR = BASE / "eda_output/corridors"
ANOM = BASE / "eda_output/anomalies"
FEAT = BASE / "eda_output/features"
INV2 = BASE / "outputs/figures/01_inventory"

# ── colour palette ────────────────────────────────────────────────────────
NAVY   = (23,  54,  93)
STEEL  = (70, 130, 180)
LIGHT  = (220, 230, 242)
WHITE  = (255, 255, 255)
DARK   = (30,  30,  30)
GRAY   = (100, 100, 100)
RED    = (180,  30,  30)
GREEN  = (30, 130,  60)

W, H = 297, 210  # A4 landscape mm

class Report(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_margins(0, 0, 0)
        self.set_auto_page_break(False)

    # ── helpers ──────────────────────────────────────────────────────────
    def _header_band(self, title, section_color=NAVY):
        self.set_fill_color(*section_color)
        self.rect(0, 0, W, 22, "F")
        self.set_fill_color(*LIGHT)
        self.rect(0, 0, 5, 22, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 16)
        self.set_xy(10, 6)
        self.cell(W - 20, 10, title, align="L")

    def _footer(self, page_num, total=14):
        self.set_fill_color(*NAVY)
        self.rect(0, H - 9, W, 9, "F")
        self.set_text_color(*LIGHT)
        self.set_font("Helvetica", "", 7)
        self.set_xy(8, H - 7)
        self.cell(W - 20, 5, "GDOT Traffic Dataset EDA  |  2017-2024  |  Georgia DOT", align="L")
        self.set_xy(W - 30, H - 7)
        self.cell(25, 5, f"Page {page_num} / {total}", align="R")

    def _body_area(self):
        """Returns (x, y, w, h) of usable body below header and above footer."""
        return 5, 24, W - 10, H - 33

    def _place_img(self, path, x, y, w, h):
        p = Path(path)
        if p.exists():
            self.image(str(p), x=x, y=y, w=w, h=h, keep_aspect_ratio=True)
        else:
            self.set_draw_color(180, 180, 180)
            self.set_fill_color(245, 245, 245)
            self.rect(x, y, w, h, "DF")
            self.set_text_color(150, 150, 150)
            self.set_font("Helvetica", "I", 8)
            self.set_xy(x + 2, y + h / 2 - 3)
            self.cell(w - 4, 5, p.name, align="C")

    def _bullets(self, x, y, w, items, font_size=9.5, spacing=5.5, color=DARK):
        self.set_text_color(*color)
        for item in items:
            self.set_xy(x, y)
            self.set_font("Helvetica", "B", font_size)
            self.cell(4, spacing, "-")
            self.set_font("Helvetica", "", font_size)
            self.set_xy(x + 4, y)
            self.multi_cell(w - 4, spacing, item, align="L")
            y = self.get_y() + 1
        return y

    def _kv_table(self, x, y, w, rows, col_ratio=0.5, font_size=9):
        col1 = w * col_ratio
        col2 = w * (1 - col_ratio)
        self.set_font("Helvetica", "", font_size)
        for i, (k, v) in enumerate(rows):
            fill = i % 2 == 0
            if fill:
                self.set_fill_color(*LIGHT)
            else:
                self.set_fill_color(*WHITE)
            self.set_text_color(*DARK)
            self.set_xy(x, y)
            self.set_font("Helvetica", "B", font_size)
            self.cell(col1, 6, f"  {k}", fill=fill, border=0)
            self.set_font("Helvetica", "", font_size)
            self.cell(col2, 6, str(v), fill=fill, border=0)
            y += 6
        return y

    def _section_label(self, x, y, text, color=STEEL):
        self.set_fill_color(*color)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(x, y)
        self.cell(0, 5, f"  {text}  ", fill=True)
        return y + 6

    # ── slide builders ────────────────────────────────────────────────────

    def slide_title(self):
        self.add_page()
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, H, "F")
        self.set_fill_color(*STEEL)
        self.rect(0, 80, W, 2, "F")
        self.set_fill_color(255, 200, 0)
        self.rect(0, 0, 6, H, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 28)
        self.set_xy(15, 55)
        self.cell(W, 14, "GDOT Traffic Dataset", align="L")
        self.set_font("Helvetica", "B", 22)
        self.set_xy(15, 72)
        self.cell(W, 10, "Exploratory Data Analysis", align="L")
        self.set_font("Helvetica", "", 14)
        self.set_xy(15, 90)
        self.cell(W, 8, "2017 - 2024  |  Georgia Department of Transportation", align="L")
        self.set_font("Helvetica", "", 11)
        self.set_xy(15, 110)
        self.cell(W, 6, "286 Stations  *  3 Data Tiers  *  7 Analysis Tracks", align="L")
        self._footer(1)

    def slide_exec_summary(self):
        self.add_page()
        self._header_band("Executive Summary")
        bx, by, bw, bh = self._body_area()

        # left: key numbers table
        lw = bw * 0.48
        self._section_label(bx, by, "Dataset at a Glance")
        rows = [
            ("Stations in catalog", "330  (286 with data)"),
            ("Data tiers", "3  (5-min 2024 / 5-min 2022-23 / Hourly 2017-22)"),
            ("Coverage window", "2017 - 2024  (8 years)"),
            ("Station-months", "21,837 total"),
            ("Complete station-months", "19,998  (91.6%)"),
            ("Fleet missingness rate", "8.4%"),
            ("Functional classes", "7  (FC1 Interstate dominant, 42%)"),
            ("Urban / Rural split", "~70% Urban, ~30% Rural"),
        ]
        self._kv_table(bx, by + 7, lw, rows, col_ratio=0.48, font_size=9.5)

        # right: trust & readiness
        rx = bx + lw + 6
        rw = bw - lw - 6
        self._section_label(rx, by, "Data Trust & Modeling Readiness")
        rows2 = [
            ("Trusted stations", "243  (HIGH trust, >=2 sources)"),
            ("CAUTION stations", "36  (usable with caveats)"),
            ("EXCLUDED stations", "7  (flagged for investigation)"),
            ("Trusted station-months", "19,963  (96.9%)"),
            ("Anomaly-days detected", "391  (90.5% explained by event flags)"),
            ("Reference station candidates", "27  (all 5 quality criteria)"),
            ("Clean hourly records (2024)", "818,645  (99 stations)"),
            ("Station feature table", "286 stations x 27 features"),
        ]
        self._kv_table(rx, by + 7, rw, rows2, col_ratio=0.52, font_size=9.5)

        self._footer(2)

    def slide_architecture(self):
        self.add_page()
        self._header_band("Dataset Architecture & Schema Overview", STEEL)
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.52
        self._place_img(INV2 / "01_station_catalog_profiling.png", bx, by, lw, bh)

        rx = bx + lw + 5
        rw = bw - lw - 5
        self._section_label(rx, by, "Three-Tier Architecture")
        rows = [
            ("Tier 1 (2024)", "5-min, directional, speed & weight bins"),
            ("Tier 2 (2022-23)", "5-min, lane-level, no speed/weight"),
            ("Tier 3 (2017-22)", "Hourly, directional, AvgSpeed + QC flags"),
            ("All-3-tier overlap", "225 stations  (78.7%)"),
            ("Exactly 2-tier", "27 stations"),
            ("Single-tier only", "34 stations"),
        ]
        y = self._kv_table(rx, by + 7, rw, rows, col_ratio=0.42, font_size=9)

        y = self._section_label(rx, y + 4, "Known Schema Issues")
        self._bullets(rx, y, rw, [
            "Station ID: 12-digit COSIT (Tier 1) vs XXX-XXXX (Tiers 2-3) - requires lookup map",
            "2 non-standard IDs (021-w334, 185-w227) prevent reliable cross-tier joins",
            "Tier 2 lacks speed/weight bins; Tier 3 is hourly not 5-min",
            "High metadata nulls (Bridge ID 99.7%, LTPP 98.8%) are field-type artefacts, not quality failures",
        ], font_size=9)
        self._footer(3)

    def slide_inventory(self):
        self.add_page()
        self._header_band("Data Inventory - Stations, Functional Class & Coverage", STEEL)
        bx, by, bw, bh = self._body_area()

        hw = bw * 0.38
        hh = bh * 0.5 - 2
        self._place_img(INV / "fig_functional_class.png",     bx,        by,        hw, hh)
        self._place_img(INV / "fig_urban_rural.png",           bx + hw + 3, by,      hw, hh)
        self._place_img(INV2 / "04_stations_per_year.png",    bx,        by + hh + 3, hw * 2 + 3, hh - 2)

        rx = bx + hw * 2 + 9
        rw = bw - hw * 2 - 9
        self._section_label(rx, by, "Key Numbers")
        self._bullets(rx, by + 7, rw, [
            "FC1 Interstate: 139 stations (42%) - largest class",
            "FC3 Other Principal Arterial: 77 stations (23%)",
            "FC4 Minor Arterial: 52 * FC5 Major Collector: 34",
            "Urban Interstate leads urban split (115 stations)",
            "Active stations declining: 258 (2018) -> 233 (2024)",
            "Mean complete months per station: 72.9 (median 84.0)",
        ], font_size=9.5)
        self._footer(4)

    def slide_completeness(self):
        self.add_page()
        self._header_band("Completeness & Coverage by Tier and Station", STEEL)
        bx, by, bw, bh = self._body_area()

        iw = bw * 0.4
        ih = bh * 0.52
        self._place_img(INV2 / "02_completeness_2024.png",         bx,      by,       iw,     ih)
        self._place_img(INV2 / "03_completeness_heatmap_2024.png", bx,      by+ih+2, iw,     bh-ih-2)
        self._place_img(INV2 / "05_completeness_by_road_class.png",bx+iw+3, by,      bw-iw-3, bh)

        self._footer(5)

    def slide_missingness_audit(self):
        self.add_page()
        self._header_band("Missingness Audit - Overall & Temporal Patterns")
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.63
        lh1 = bh * 0.54
        lh2 = bh - lh1 - 2
        self._place_img(MISS / "fig_missingness_by_station_heatmap.png", bx, by,       lw, lh1)
        self._place_img(MISS / "fig_missingness_by_year.png",            bx, by+lh1+2, lw, lh2)

        rx = bx + lw + 5
        rw = bw - lw - 5
        self._section_label(rx, by, "Fleet-Wide Findings")
        self._bullets(rx, by + 7, rw, [
            "Overall missingness: 8.4% of station-months below 80% coverage",
            "73.4% of stations are 'always-on' (>=90% complete months)",
            "Only 1.8% are chronically sparse (<40% complete months)",
            "226 outage runs identified; 73 runs exceed 6 months (max 60)",
        ], font_size=9.5)

        y = self._section_label(rx, by + 52, "Year-over-Year Trend")
        self._bullets(rx, y, rw, [
            "2017: 13.6% - incomplete initial deployment coverage",
            "2022-23: 12% spike - system transition to 5-min pipeline",
            "2024: 7.8% - partial recovery",
            "Pattern is operationally-driven, NOT random (not MCAR)",
        ], font_size=9.5)
        self._footer(6)

    def slide_missingness_patterns(self):
        self.add_page()
        self._header_band("Missingness Patterns - Functional Class, Run Length & Hour Bias")
        bx, by, bw, bh = self._body_area()

        iw = bw * 0.3
        ih = bh * 0.5 - 2
        self._place_img(MISS / "fig_missingness_by_fc.png",        bx,        by,       iw * 1.1, bh)
        self._place_img(MISS / "fig_run_length_distribution.png",  bx+iw*1.1+2, by,     iw,     ih)
        self._place_img(MISS / "fig_dow_bias_sample.png",          bx+iw*1.1+2, by+ih+2, iw,     ih)
        self._place_img(MISS / "fig_hourly_bias_sample.png",       bx+iw*2.1+4, by,     iw,     ih)

        rx = bx + iw * 3.1 + 7
        rw = bw - iw * 3.1 - 7
        self._section_label(rx, by, "Key Patterns")
        self._bullets(rx, by + 7, rw, [
            "FC1 Interstate: 13.5% miss - highest class",
            "FC2 Freeways: 14.6% - likely multi-lane bin methodology",
            "FC3-5 Arterials/Collectors: only 3.2-5.4%",
            "52% of outage runs are single-month (routine maintenance)",
            "32% of runs exceed 6 months (sensor replacement cycles)",
            "Peak missingness at hour 6 (early morning); lowest at hour 16",
            "6.5% of 2024 bins show zero count with >50% coverage",
        ], font_size=9)
        self._footer(7)

    def slide_traffic_behavior(self):
        self.add_page()
        self._header_band("Baseline Traffic Behavior - Profiles & Distributions")
        bx, by, bw, bh = self._body_area()

        iw = bw * 0.36
        ih = bh * 0.5 - 2
        self._place_img(PROF / "fig_hourly_profile_by_fc.png",     bx,       by,       iw*1.4, bh)
        self._place_img(PROF / "fig_dow_profile_by_fc.png",        bx+iw*1.4+2, by,   iw,     ih)
        self._place_img(PROF / "fig_weekday_weekend_ratio.png",    bx+iw*1.4+2, by+ih+2, iw, ih)

        rx = bx + iw * 2.4 + 5
        rw = bw - iw * 2.4 - 5
        self._section_label(rx, by, "Volume Summary (100 stations, 2024)")
        rows = [
            ("Median daily volume", "22,830 veh/day"),
            ("Mean daily volume",   "45,223 veh/day"),
            ("FC2 Freeways (median)", "~110K veh/day"),
            ("FC1 Interstate (median)", "~52K veh/day"),
            ("FC3 OPA (median)",     "~19K veh/day"),
            ("W/WE ratio (fleet)", "1.25 (weekday-heavy)"),
            ("AM peak hour",        "07:00 (stable)"),
            ("PM peak hour",        "17:00 (stable)"),
        ]
        y = self._kv_table(rx, by + 7, rw, rows, col_ratio=0.55, font_size=9)

        y = self._section_label(rx, y + 3, "Archetype Note")
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(*GRAY)
        self.set_xy(rx, y)
        self.multi_cell(rw, 4.5,
            "Station archetype clustering (k-means) collapsed to 77/78 stations "
            "'Mixed' using 2024-only features. Functional class used as primary "
            "stratifier; archetype modeling deferred pending multi-year directional data.", align="L")
        self._footer(8)

    def slide_temporal_trends(self):
        self.add_page()
        self._header_band("Temporal Trends - AADT, Seasonality & Decomposition")
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.56
        lh1 = bh * 0.46
        self._place_img(TREN / "fig_aadt_trend_2017_2024.png",           bx, by,        lw, lh1)
        self._place_img(TREN / "fig_seasonal_decomposition_examples.png", bx, by+lh1+2, lw, bh-lh1-2)

        rx = bx + lw + 5
        rw = bw - lw - 5
        self._section_label(rx, by, "AADT Trends (30-station sample, 2018-2023)")
        self._bullets(rx, by + 7, rw, [
            "COVID-19 impact: ~8.6% volume drop (2019->2020) across all FC",
            "Recovery visible by 2021-22; FC2 freeways recovered fastest",
            "AADT proxy = June mean daily volume (June is least seasonally biased)",
        ], font_size=9.5)

        y = self._section_label(rx, by + 42, "Seasonality (2023 baseline)")
        self._bullets(rx, y, rw, [
            "Peak month: October (Seasonal Index = 1.036)",
            "Trough month: January (SI = 0.928) - +/-10% annual amplitude",
            "Rural FC4-5 stations show stronger seasonality than Interstate",
            "Peak-hour structure (AM 7:00, PM 17:00) stable across all 4 seasons",
        ], font_size=9.5)
        self._footer(9)

    def slide_holiday_effects(self):
        self.add_page()
        self._header_band("Holiday & Long Weekend Traffic Effects - 2024")
        bx, by, bw, bh = self._body_area()

        iw = bw * 0.4
        ih = bh * 0.54
        self._place_img(TREN / "fig_holiday_effect.png",       bx,      by,      iw * 1.3, ih)
        self._place_img(TREN / "fig_long_weekend_effects.png", bx,      by+ih+2, iw * 1.3, bh-ih-2)
        self._place_img(INV2 / "06_event_flag_overview.png",   bx+iw*1.3+3, by,  bw-iw*1.3-3, bh)

        self._footer(10)

    def slide_corridor_relationships(self):
        self.add_page()
        self._header_band("Inter-Station Relationships & Corridor Structure", GREEN)
        bx, by, bw, bh = self._body_area()

        iw = bw * 0.4
        self._place_img(CORR / "fig_correlation_heatmap.png",    bx,      by,  iw, bh)
        self._place_img(CORR / "fig_geographic_clusters_map.png",bx+iw+3, by,  iw, bh)

        rx = bx + iw * 2 + 7
        rw = bw - iw * 2 - 7
        self._section_label(rx, by, "Pairwise Correlation (top 80 stations)")
        rows = [
            ("Valid pairs", "2,848 (>=180 overlapping days)"),
            ("Mean Pearson r", "0.573  (median 0.636)"),
            ("Range", "-0.24 to 0.993"),
            ("High-corr pairs (r>0.85)", "411  (14.4%)"),
        ]
        y = self._kv_table(rx, by + 7, rw, rows, col_ratio=0.56, font_size=9)

        y = self._section_label(rx, y + 3, "Clustering & Reference Stations")
        self._bullets(rx, y, rw, [
            "44 cluster IDs; 7 multi-station corridor clusters",
            "37 singletons - no close behavioral neighbors in sample",
            "211 behavioral neighbor pairs (r>0.7 AND dist<50km)",
            "27 reference station candidates passed all 5 quality criteria",
            "Top candidate: 089-3323 (DeKalb, Interstate, 10 neighbors)",
            "Coverage note: top 80 stations only - 150+ eligible not assessed",
        ], font_size=9)
        self._footer(11)

    def slide_anomalies(self):
        self.add_page()
        self._header_band("Anomaly Detection & Station Trustworthiness", RED)
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.56
        lh1 = bh * 0.56
        self._place_img(ANOM / "fig_anomaly_timeline.png",        bx, by,       lw, lh1)
        self._place_img(ANOM / "fig_trust_tier_distribution.png", bx, by+lh1+2, lw, bh-lh1-2)

        rx = bx + lw + 5
        rw = bw - lw - 5
        self._section_label(rx, by, "Anomaly Detection (58 stations, 2024)")
        rows = [
            ("Total anomaly-days", "391"),
            ("Explained by event flags", "354  (90.5%)"),
            ("Unexplained anomaly-days", "37  (9.5%)"),
        ]
        y = self._kv_table(rx, by + 7, rw, rows, col_ratio=0.6, font_size=9.5)

        y = self._section_label(rx, y + 4, "Station-Month Trustworthiness (286 stations)")
        rows2 = [
            ("TRUSTED months", "19,963  (96.9%)"),
            ("CAUTION months", "233  (1.1%)"),
            ("EXCLUDE months", "404  (2.0%)"),
        ]
        y = self._kv_table(rx, y, rw, rows2, col_ratio=0.6, font_size=9.5)

        y = self._section_label(rx, y + 4, "Station-Level Trust Tiers")
        rows3 = [
            ("TRUSTED stations", "243  (84.9%)"),
            ("CAUTION stations", "36  (12.6%)"),
            ("EXCLUDED stations", "7  (2.5%)"),
        ]
        self._kv_table(rx, y, rw, rows3, col_ratio=0.6, font_size=9.5)
        self._footer(12)

    def slide_modeling_readiness(self):
        self.add_page()
        self._header_band("Modeling Readiness - Clean Datasets & Feature Engineering", GREEN)
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.5
        self._place_img(FEAT / "fig_aggregation_comparison.png", bx, by, lw, bh)

        rx = bx + lw + 5
        rw = bw - lw - 5
        self._section_label(rx, by, "Clean Hourly Dataset (2024)")
        rows = [
            ("Hourly records", "818,645"),
            ("Trusted stations covered", "99 of 207 eligible"),
            ("Temporal span", "Full calendar year 2024"),
            ("Mean coverage", "100%  (min 50%)"),
            ("Imputed hours", "1.7% (< 6 valid 5-min bins)"),
            ("Median hourly volume", "580 veh/hr  (max 17,822)"),
        ]
        y = self._kv_table(rx, by + 7, rw, rows, col_ratio=0.52, font_size=9.5)

        y = self._section_label(rx, y + 4, "Station Feature Table")
        rows2 = [
            ("Dimensions", "286 stations x 27 features"),
            ("AADT proxy", "median_daily x 365 (June-ref)"),
            ("Seasonal amplitude", "per station from 2023"),
            ("Trust tier flag", "is_trusted_2024"),
            ("Recommended resolution", "Hourly (balances noise vs. signal)"),
        ]
        y = self._kv_table(rx, y, rw, rows2, col_ratio=0.52, font_size=9.5)

        y = self._section_label(rx, y + 4, "Recommended Modeling Phases")
        self._bullets(rx, y, rw, [
            "Phase A: AADT estimation (gradient boosting, 286-station feature table)",
            "Phase B: Gap-filling via 27 reference station behavioral neighbors",
            "Phase C: Anomaly-adjusted counts (exclude 37 unexplained days)",
            "Phase D: Archetype modeling - DEFERRED (needs multi-year data)",
        ], font_size=9)
        self._footer(13)

    def slide_gaps_next_steps(self):
        self.add_page()
        self._header_band("Known Gaps & Recommended Next Steps", (120, 60, 0))
        bx, by, bw, bh = self._body_area()

        lw = bw * 0.48
        y = self._section_label(bx, by, "Open Items (action required before full modeling)")
        self._bullets(bx, y, lw, [
            "100-station pipeline cap: 207 trusted stations eligible; only 99 processed - hourly dataset covers 48% of population. Remove cap and re-run.",
            "Archetype labels: k-means collapsed (77/78 'Mixed'). Deferred until multi-year directional features and full 207-station sample are available.",
            "Corridor analysis scope: correlation matrix covers only top 80 of ~230 eligible stations. Expand to full set, relax min_periods 180->90 days.",
            "5 chronic-sparse stations (<40% complete months): status unknown - decommissioned, relocated, or persistently failing? Cross-reference GDOT field logs.",
        ], font_size=9.5, spacing=5)

        rx = bx + lw + 6
        rw = bw - lw - 6
        y2 = self._section_label(rx, by, "Risks & Mitigations")
        self._bullets(rx, y2, rw, [
            "AADT proxy accuracy: degrades for stations with seasonal amplitude >0.4 - apply seasonal adjustment for high-amplitude stations.",
            "2022-23 missingness spike (12%) may bias longitudinal models - flag period; run models with and without.",
            "Interstate/freeway missingness (13-15%) may reflect multi-lane expected-bin methodology, not sensor failure - validate before imputing.",
            "37 unexplained anomaly-days: exclude from model training; audit against weather and incident records.",
            "Non-standard IDs (021-w334, 185-w227): build explicit COSIT lookup and add station_type flag.",
        ], font_size=9.5, spacing=5)

        # bottom banner
        self.set_fill_color(*LIGHT)
        self.rect(bx, H - 38, bw, 16, "F")
        self.set_text_color(*NAVY)
        self.set_font("Helvetica", "B", 10)
        self.set_xy(bx + 4, H - 36)
        self.cell(bw, 6, "Bottom Line: 243 trusted stations, 818K clean hourly records, and 286-station feature table are ready for AADT modeling.", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_xy(bx + 4, H - 30)
        self.cell(bw, 6, "Holiday effects now quantified. Archetype modeling and full corridor analysis are the two main deferred items.", align="L")
        self._footer(14)


# ── generate ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rpt = Report()
    rpt.slide_title()
    rpt.slide_exec_summary()
    rpt.slide_architecture()
    rpt.slide_inventory()
    rpt.slide_completeness()
    rpt.slide_missingness_audit()
    rpt.slide_missingness_patterns()
    rpt.slide_traffic_behavior()
    rpt.slide_temporal_trends()
    rpt.slide_holiday_effects()
    rpt.slide_corridor_relationships()
    rpt.slide_anomalies()
    rpt.slide_modeling_readiness()
    rpt.slide_gaps_next_steps()
    rpt.output(str(OUT_PDF))
    print(f"Saved: {OUT_PDF}  ({OUT_PDF.stat().st_size // 1024} KB)")
