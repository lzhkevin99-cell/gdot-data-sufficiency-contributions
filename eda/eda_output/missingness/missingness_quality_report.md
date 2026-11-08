# GDOT Traffic Data — Missingness Quality Audit Report
**Phase 1B | Generated:** 2026-04-10
**Script:** `missingness_quality_agent.py`

---

## Objective

Perform a deep missingness audit of the GDOT continuous count station (CCS) dataset spanning 2017–2024. The goal is to characterize where, when, and how severely data are absent or degraded across stations, functional classes, and time — and to assess whether missingness exhibits structured patterns (temporal, geographic, or sensor-related) that would affect downstream analysis.

---

## Methods

**Data sources:**
- Three pre-computed completeness CSVs (2017–2022 directional monthly files, 2022–2023 lane-level monthly files, 2024 5-min CCS files). Each provides observed vs. expected bin counts per station-month, yielding `completeness_pct`.
- Station master table (Phase 1A) for functional class, urban/rural, and date-range metadata.
- Raw 2024 5-min files (CCS_5Min_2024) for sub-daily bias analysis; a stratified sample of 50 stations across FC categories was used to avoid loading the full ~33 GB dataset.

**Missingness classification tiers:**
| Flag | Coverage % |
|------|-----------|
| COMPLETE | ≥ 80% |
| PARTIAL_MINOR | 60–80% |
| PARTIAL_MAJOR | 40–60% |
| SPARSE | 0–40% (>0) |
| ABSENT | 0% / no record |

A full station × month grid was constructed for each station's observed date range (from `first_date` to `last_date` in the station master). Months not appearing in any completeness CSV are classified as ABSENT.

**Hour-of-day / day-of-week bias:** Missingness defined as 5-min bins where `Coverage % == 0` (sensor inactive or no data received). Analyzed across 8,414,880 records from 50 sampled stations.

**Outage style thresholds:** based on fraction of station-months classified COMPLETE:
- `always_on`: ≥ 90% complete months
- `occasional_gap`: 70–90%
- `seasonal_dropout`: 40–70%
- `chronic_sparse`: < 40%

---

## Key Findings

### Fleet-wide completeness
- **286 stations** analyzed across **21,837 station-months** (2017–2024).
- **19,998 station-months (91.6%)** are COMPLETE (≥ 80% coverage).
- **1,237 station-months (5.7%)** are ABSENT (no record at all within the station's operational period).
- **Overall missingness rate: 8.4%** (fraction of station-months not achieving ≥ 80% coverage).

### Outage style distribution
| Style | N Stations | % of Fleet | Criteria |
|-------|-----------|-----------|---------|
| always_on | 210 | 73.4% | ≥ 90% complete months |
| occasional_gap | 45 | 15.7% | 70–90% |
| seasonal_dropout | 26 | 9.1% | 40–70% |
| chronic_sparse | 5 | 1.8% | < 40% |

The majority of the fleet is highly reliable. However, 31 stations (10.8%) have 30–60% of their months absent or degraded — these stations require caution in any longitudinal analysis.

### Run-length analysis of outages
- 226 discrete outage runs identified (sequences of consecutive ABSENT or SPARSE months).
- Median run length: **1 month** (most outages are single-month gaps).
- **73 runs (32%) exceed 6 months** in length, with a maximum of **60 consecutive months** — indicating some stations experienced multi-year effective silence. These long outages are likely the result of equipment replacement, decommissioning, or extended sensor failure rather than random missing data.
- Short runs (1 month: 118 runs, 52%) are consistent with routine maintenance windows or data transmission failures.

### Year-over-year missingness trend
| Year | Mean Missingness Rate |
|------|----------------------|
| 2017 | 13.6% |
| 2018 | 3.7% |
| 2019 | 5.7% |
| 2020 | 7.7% |
| 2021 | 8.5% |
| 2022 | 12.0% |
| 2023 | 11.8% |
| 2024 | 7.8% |

2017 has elevated missingness consistent with partial data availability at the start of the export window (many stations had not yet begun reporting). 2022–2023 show a secondary peak; this may reflect sensor attrition, COVID-era staffing impacts on maintenance, or data pipeline issues during the transition to the 5-min collection system. 2024 shows improvement. These patterns **cannot be confidently attributed to MCAR (missing completely at random)**; the temporal structure is consistent with structured absence driven by operational or administrative factors.

### Missingness by functional class
| FC | Mean Missingness Rate | N Stations |
|----|----------------------|-----------|
| 2: Other Freeways / Expressways | 14.6% | 22 |
| 1: Interstate | 13.5% | 128 |
| 3: Other Principal Arterial | 5.4% | 63 |
| 4: Minor Arterial | 4.8% | 41 |
| 5: Major Collector | 3.2% | 26 |
| 6: Minor Collector | 0.0% | 1 |
| 7: Local Access | 0.0% | 2 |

Interstate and freeway/expressway stations have the **highest missingness rates** (~14%). This is counterintuitive (high-priority infrastructure) and may reflect: (a) longer binary recording gaps from multi-lane sensors, (b) greater expected bin counts making partial months harder to classify as COMPLETE, or (c) actual sensor maintenance complexity. Rural stations show lower mean missingness (5.1%) vs. urban stations (10.9%), though this likely partly reflects the FC composition difference (most urban stations are Interstates).

### Hour-of-day bias (2024, 50-station sample, 8.4M records)
- Peak missingness hour: **hour 6** (early morning). This could reflect scheduled maintenance windows or early-AM data gaps before sensor warm-up.
- Lowest missingness hour: **hour 16** (4 PM peak traffic period), consistent with higher-priority sensor activity during peak hours.
- The pattern, while present, is subtle — the overall fraction of bins with Coverage%=0 is low for most stations in this sample.

### Day-of-week bias (2024 sample)
- Peak missing day: **Wednesday** (mid-week).
- Weekends show comparable or slightly higher missingness vs. weekdays in some stations.
- Day-of-week differences are small in absolute terms; the pattern does not strongly suggest systematic weekend sensor shutoffs.

### Zero-volume and suspicious record detection (2024 sample)
- **545,270 records (6.48%)** had Count=0 with Coverage > 50%: sensor was reportedly active but recorded no vehicles. At low-volume rural sites and overnight hours, this is plausible genuine zero-traffic. At urban/interstate sites during peak hours, isolated zero-count bins warrant scrutiny as potential sensor malfunctions.
- **0 impossible records** found (no Coverage% > 100, no negative counts). Data passes basic range validation.

---

## Tables/Plots Created

| File | Description |
|------|-------------|
| `station_missingness_scorecard.csv` | 286 rows; per-station completeness metrics and outage style |
| `station_month_issue_table.csv` | 20,600 rows (observed); per station-month coverage % and quality flag |
| `outage_classification_summary.csv` | 4 rows; outage style breakdown with example stations |
| `fig_run_length_distribution.png` | Histogram of consecutive absent/sparse month run lengths |
| `fig_missingness_by_year.png` | Annual mean missingness rate 2017–2024 |
| `fig_missingness_by_fc.png` | Missingness by functional class + urban vs. rural |
| `fig_missingness_by_station_heatmap.png` | Station × year-month heatmap for top 80 stations by missing months |
| `fig_hourly_bias_sample.png` | Hour-of-day missingness rate (Coverage%=0) across 50-station sample |
| `fig_dow_bias_sample.png` | Day-of-week missingness rate across 50-station sample |

---

## Risks / Caveats

1. **ABSENT vs. never-active confusion:** Stations with short operational histories are more likely to appear ABSENT simply because they weren't deployed yet. The grid filtering by `first_date`/`last_date` mitigates this, but edge cases at the start/end of a station's life may still inflate apparent missingness.

2. **Completeness% vs. true missingness:** `completeness_pct` measures observed bins / expected bins. An expected-bin calculation that over-estimates (e.g., due to direction count mismatches between sources) could falsely depress completeness. Conversely, a station that genuinely reports no traffic but is operational would appear ABSENT.

3. **Zero-volume is not unambiguous missingness:** 6.48% of 2024 5-min bins have Count=0 with Coverage>50%. These may be genuine zero-volume periods (e.g., overnight on rural roads) rather than sensor failure. They should not be removed without location-hour context.

4. **Multi-source deduplication:** Where 2017–2022 and 2022–2023 CSVs overlap, the maximum completeness_pct was retained. This is conservative (assumes best available), but differences in how each pipeline computed expected bins mean cross-source comparisons should be treated cautiously.

5. **FC-level missingness interpretation:** Higher missingness on Interstates could reflect methodology (more lanes → higher expected bins → harder to achieve 80% threshold) rather than worse data quality per se. Verify expected-bin calculation in the completeness pipeline before concluding Interstate data is structurally worse.

6. **Temporal structure caution:** The 2022–2023 elevated missingness and the 2017 spike are consistent with structured (non-random) absence. However, the specific mechanism — whether operational, administrative, or sensor-related — cannot be determined from completeness data alone. Labeling this as MAR or MNAR requires corroborating evidence from event logs or field maintenance records.

---

## Recommended Next Steps

1. **Cross-reference outage periods with event logs** (`all_events_2024.csv`) to distinguish sensor-flagged failures from unexplained absences. Focus on the 73 outage runs > 6 months and the 5 chronic_sparse stations.

2. **Investigate the 2022–2023 missingness spike**: Check whether the elevated 12% rate corresponds to specific stations or districts, and whether it aligns with the data source transition (historical directional → 5-min lane-level collection).

3. **Validate zero-volume records by location and time**: For Interstate and urban arterial stations, zero-count bins during peak hours (7–9 AM, 4–7 PM) are suspicious and should be flagged for QC review. Low-volume rural stations at 2–4 AM can reasonably have zero-count bins.

4. **Examine chronic_sparse stations** (021-0349, 021-0372, 051-0138, and 2 others): Determine whether these are candidates for exclusion from trend analysis, or whether partial data can still support seasonal or directional metrics.

5. **Refine COMPLETE threshold sensitivity**: The 80% threshold is conventional. Test whether conclusions change at 70% or 90% thresholds, particularly for the FC-level comparison where methodology differences may confound the Interstate result.

6. **Hour-of-day analysis with directional decomposition**: The peak-morning missingness at hour 6 warrants deeper investigation — check whether this concentrates in specific FC groups or specific districts, which would suggest maintenance-schedule patterns.
