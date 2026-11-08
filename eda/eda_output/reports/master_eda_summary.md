# GDOT EDA Master Summary

**Generated:** 2026-04-10
**EDA Phase:** 5 — Final Synthesis
**Data window:** 2017–2024
**Agents completed:** 7 of 7

---

## 1. Data Inventory and Structure

The GDOT continuous count station (CCS) dataset spans three distinct data tiers covering 2017–2024. The canonical station catalog contains **330 stations** with 330 unique COSIT values. After cross-referencing source presence files, **286 stations** appear in at least one data tier; **283 of these** could be matched to full catalog metadata. The remaining 3 stations have minor join-key issues (COSIT vs. station_name format mismatches).

**Tier composition and coverage:**
- **Tier 1 — CCS_5Min_2024**: 5-minute resolution, directional (N/S/E/W), includes speed bins (<10 mph through >80 mph) and weight class bins. Station ID encoded as 12-digit zero-padded COSIT in the filename.
- **Tier 2 — GDOT_CCS_2022–2023**: 5-minute resolution, lane-level stratification, no speed or weight bins. Station ID in `XXX-XXXX` format.
- **Tier 3 — GDoT_UGA_Directional_2017–2022**: Hourly resolution, directional, includes AvgSpeed and VolumeQC/ClassQC flags but no bin distributions.

**Tier overlap:** 225 stations (78.7% of the 286-station working set) appear in all three tiers, 27 in exactly two, and 34 in only one. The mean number of complete months per station across all tiers is **72.9**, with a median of **84.0**. Tier-level complete-month rates are: 93.3% (Tier 2), 94.9% (Tier 1), and 98.8% (Tier 3).

**Station mix:** The fleet is Interstate-heavy — 139 stations (42%) are classified as Interstate (FC1), followed by 77 Other Principal Arterial (FC3), 52 Minor Arterial (FC4), 34 Major Collector (FC5), and 23 Other Freeways/Expressways (FC2). Geographically, 115 stations are Urban Interstate, 52 Urban Other Principal Arterial, and 38 Urban Minor Arterial; 25 and 24 stations are Rural Other Principal Arterial and Rural Interstate, respectively.

**Known structural issues:** Two station IDs use non-standard 'w'-suffix formats (`021-w334`, `185-w227`), preventing reliable cross-tier joins. The Tier 1 filename format differs from Tier 2/3 (12-digit COSIT vs. `XXX-XXXX`), requiring a derivation mapping. Several metadata columns have very high null rates (Bridge ID: 99.7%, LTPP Site ID: 98.8%) but these are field-type-specific, not data quality failures.

---

## 2. Data Quality and Missingness

The missingness audit covered all **286 stations** across **21,837 station-months** (2017–2024). Using a primary threshold of ≥80% bin coverage to classify a station-month as COMPLETE:

- **19,998 station-months (91.6%)** are COMPLETE.
- **1,237 station-months (5.7%)** are classified as ABSENT (no record within the station's observed operational window).
- **Overall fleet-wide missingness rate: 8.4%** (fraction of station-months not meeting the COMPLETE threshold).

**Outage style distribution:**
| Style | Stations | % of Fleet |
|-------|----------|-----------|
| always_on (≥90% complete months) | 210 | 73.4% |
| occasional_gap (70–90%) | 45 | 15.7% |
| seasonal_dropout (40–70%) | 26 | 9.1% |
| chronic_sparse (<40%) | 5 | 1.8% |

The majority of the fleet is operationally reliable. However, **31 stations (10.8%)** have 30–60% of their months absent or degraded and require caution in longitudinal analysis. Outage run-length analysis identified **226 discrete outage runs**; 52% are single-month gaps (consistent with maintenance), but **73 runs (32%) exceed 6 months**, with a maximum of 60 consecutive months — indicative of sensor replacement cycles or extended decommissioning.

**Year-over-year missingness:** Missingness was highest in 2017 (13.6%), consistent with incomplete export coverage at the start of the data window. A secondary peak appears in 2022–2023 (12.0% and 11.8%), possibly reflecting sensor attrition or the pipeline transition from directional to lane-level collection. 2024 shows recovery to 7.8%. These temporal patterns are inconsistent with missing-completely-at-random (MCAR) and suggest structured, operationally-driven absence.

**Functional class disparities:** Interstates (FC1) and Other Freeways/Expressways (FC2) show the highest missingness rates — 13.5% and 14.6% respectively — compared to 5.4% (FC3), 4.8% (FC4), and 3.2% (FC5). This is counterintuitive for high-priority infrastructure and may partially reflect methodology: multi-lane sensors produce higher expected bin counts, making the 80% COMPLETE threshold harder to satisfy.

**Sub-daily patterns (2024 sample, 50 stations, 8.4M records):** Peak missingness occurs at **hour 6** (early morning); the lowest missingness hour is **hour 16** (PM peak). Wednesday is the peak missing day-of-week, though day-of-week differences are small in absolute terms. **6.48% of 2024 bins** had Count=0 with Coverage >50%, which may reflect genuine zero-volume periods at low-traffic rural sites rather than sensor failure.

---

## 3. Traffic Behavior Profiles

Traffic profiles were computed from 2024 5-minute CCS data using a stratified sample of **100 stations** (eligibility: in_5min_2024 = True AND pct_complete > 0.70; 208 stations eligible). Only bins with Coverage ≥50% were retained.

**Volume summary:**
- Median daily volume across all sampled stations: **22,830 counts/day**
- Mean daily volume: **45,223 counts/day** (mean significantly exceeds median due to high-volume Interstate/freeway stations)
- Median weekday/weekend ratio: **1.25** — most stations carry more weekday traffic
- Most common AM peak hour: **7:00**; PM peak hour: **17:00**

**Volume by functional class:**
| Functional Class | Stations | Median Daily Volume | Weekday/Weekend Ratio |
|-----------------|----------|--------------------|-----------------------|
| 1: Interstate | 38 | 51,718 | 1.08 |
| 2: Other Freeways / Expressways | 6 | 110,252 | 1.22 |
| 3: Other Principal Arterial | 26 | 19,374 | 1.35 |
| 4: Minor Arterial | 18 | 12,076 | 1.35 |
| 5: Major Collector | 12 | 1,894 | 1.44 |

Freeways/expressways carry the highest volumes (~110,000/day median). Interstate weekday/weekend ratios are notably lower (1.08) than arterials and collectors (1.35–1.44), consistent with Interstates serving a mix of commuter and freight/recreational travel throughout the week.

**Seasonality (2023, 30-station sample):** Peak traffic month is **October** (seasonality index = 1.036); trough is **January** (SI = 0.928). Rural stations (FC 4–5) show stronger seasonality than urban/interstate stations. The seasonal amplitude is modest — approximately ±10% around the annual mean.

**COVID-19 impact:** The 2019–2020 comparison shows a median volume drop of approximately **8.6%** across the 30-station AADT trend sample. Post-2020 recovery is visible by 2021–2022 across all functional class categories.

**Archetype analysis:** k-means clustering (k=4) on weekday/weekend ratio, AM/PM peak hour, percent heavy vehicle, and normalized median daily volume produced poor separation — **77 of 78 classified stations** were labeled "Mixed" (one labeled "Freight/Arterial"). This collapse indicates that 2024-only features and a 100-station sample are insufficient to discriminate behavioral archetypes. Multi-year features and richer vehicle class data are required.

**Holiday effects:** Holiday effect analysis returned NaN for all 6 holidays analyzed due to a COSIT format mismatch when loading 2024 per-station files. This is an open item requiring a pipeline fix before holiday adjustment factors can be applied.

---

## 4. Temporal Trends

Temporal trend analysis used a 30-station stratified sample from the 225 three-tier stations, covering 2018–2023 AADT proxies derived from June reference-month sampling.

**AADT trends:** Mean June daily volume across selected stations was **26,692 vehicles/day**. The annual AADT proxy dataset covers years 2018–2023. Post-COVID recovery is visible in the data by 2021–2022 across functional classes. The 2019–2020 drop is observed but confounded by data coverage changes concurrent with COVID-era disruptions.

**Peak-hour stability:** AM and PM peak hours were assessed across January, April, July, and October 2023. Peak hours are stable across seasons for most stations, reinforcing the 7 AM and 5 PM modal peaks identified in the profiling phase.

**Known caveat — holiday and long-weekend effects:** The holiday effect analysis loaded 1,980 holiday-flag records from all_events_2024.csv but returned NaN effect ratios for all six major holidays (New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas). This failure was caused by a station file matching issue between COSIT-format event records and per-station file naming in CCS_5Min_2024. Long-weekend effects could not be computed for the same reason. These analyses are open items requiring a fix to the COSIT–station_name resolution logic before holiday adjustment factors can be produced.

---

## 5. Inter-Station Relationships and Corridor Structure

Corridor analysis used the **top 80 stations** by data completeness (from the 230 stations with in_5min_2024=True and n_sources≥2). Daily volume matrices were constructed from 2024 raw 5-minute data (Coverage ≥50%), yielding a 366×80 date-station matrix.

**Pairwise correlation results:**
- **2,848 valid station pairs** (≥180 overlapping days)
- Mean pairwise Pearson r = **0.573**; median = **0.636**
- Range: -0.240 to 0.993
- **411 high-correlation pairs (r > 0.85)**, representing 14.4% of all valid pairs

**Clustering:** Hierarchical clustering at a distance threshold of 0.15 (r > 0.85) produced **44 cluster IDs**. Of these, **7 are multi-station corridor clusters** containing meaningful groupings of behaviorally similar stations; **37 are singletons**, indicating that over half the analyzed stations lack a close behavioral neighbor within the sampled set.

**Behavioral neighbors:** 211 station pairs qualify as behavioral neighbors (r > 0.7 AND distance < 50 km), spread across 705 individual station-neighbor relationships.

**Reference station candidates:** **27 stations** passed all five reference station criteria: pct_complete ≥ 0.85, complete_months ≥ 10, ≥2 behavioral neighbors, n_sources = 3, and non-singleton cluster membership. These candidates are geographically distributed across Dekalb, Cherokee, Barrow, Chatham, Fulton, Cobb, Bibb, Clayton, Gwinnett, Liberty, Bartow, Clarke, Walton, Thomas, and Pickens counties. The top candidates by behavioral neighbor count are station 089-3323 (DeKalb, Interstate, 10 neighbors) and 057-0341 (Cherokee, Minor Collector, 8 neighbors).

**Caveat:** The correlation analysis covers only the top 80 stations by completeness; stations ranked 81+ may form additional corridor groups not captured. Corridor clusters are based purely on temporal volume co-movement — they do not guarantee physical road-network adjacency.

---

## 6. Anomalies and Trustworthiness

Anomaly detection used a 58-station sample with readable raw 2024 5-min data files (from a target of 60; 2 were unreadable). An IQR-based method (flags days with volume < median − 3×IQR or > median + 3×IQR) and a low-volume rule (volume < 10% of station median) were applied.

**Anomaly detection:**
- Total anomaly-days detected: **391** across 58 stations
- Explained by event flags (holiday, volume bad, outlier, atypical, roadworks, closure, accident): **354 (90.5%)**
- Unexplained anomaly-days: **37 (9.5%)**

The high explained rate (90.5%) validates the event flag system as a reliable cross-check. The 37 unexplained anomaly-days do not necessarily indicate sensor errors — they may reflect events not logged in all_events_2024.csv.

**Station-month trustworthiness across all 286 stations:**
| Tier | Station-Months | % of Total |
|------|---------------|-----------|
| TRUSTED | 19,963 | 96.9% |
| CAUTION | 233 | 1.1% |
| EXCLUDE | 404 | 2.0% |

**Station-level trust:**
| Tier | Stations |
|------|----------|
| TRUSTED | 243 |
| CAUTION | 36 |
| EXCLUDED | 7 |

**243 stations (84.9% of the 286-station fleet)** qualify for the trusted station list (HIGH trust tier, ≥2 sources, ≥8 trusted months). 36 CAUTION stations can be used with caveats; 7 stations are flagged for investigation or exclusion. The trustworthiness assessment for stations outside the 58-station raw-data sample relies on coverage proxy (quality_flag from the missingness audit) rather than volume-level anomaly detection, which may underestimate anomaly risk for those stations.

---

## 7. Modeling Readiness

The feature pipeline processed **99 trusted stations** from the 2024 CCS data (207 stations met trust criteria; capped at 100 for the pipeline run; 1 was unreadable, yielding 99).

**Clean hourly dataset:**
- Total hourly records: **818,645**
- Columns: 26 (including temporal features: date, hour_of_day, day_of_week, month, is_weekday)
- Mean hourly coverage: 100.0%; minimum: 50.0% (by design)
- Imputed-flagged hours (n_bins < 6): **1.7%** of retained hours
- Median hourly volume: **580 vehicles/hour**; maximum: **17,822 vehicles/hour**
- Saved as CSV (104MB) rather than Parquet due to missing pyarrow dependency

**Station feature table:** 286 stations × 27 features, including functional class, urban/rural designation, AADT 2023 proxy, seasonal amplitude, n_sources, pct_complete, and derived flags. The feature table covers all stations regardless of trust tier, enabling downstream filtering.

**Derived AADT estimate:** `aadt_2024_estimate = median_daily_volume × 365` provides a June-reference-free AADT proxy for 100 processed stations. Accuracy degrades for stations with seasonal amplitude > 0.4 (high seasonality).

**Modeling-ready station counts:**
- 286 stations in master table (full population)
- 243 stations in trusted list (HIGH trust, ≥2 sources)
- 211 stations with ≥6 trusted 2024 months
- 100 stations with processed hourly data (pipeline cap)
- 27 reference station candidates (highest-quality imputation donors)

**Known gaps before modeling:**
1. Holiday and long-weekend effect ratios cannot be applied until the COSIT format mismatch is resolved.
2. Archetype labels are unreliable (77/78 stations labeled "Mixed") — archetype-stratified modeling cannot proceed without richer features.
3. The hourly dataset covers only 100 of 207 eligible trusted stations; processing the full set requires removing the pipeline cap.
4. Parquet output requires pyarrow installation for efficient large-dataset handling.
5. Direction-level (NB/SB) splits are not in the hourly dataset — all lanes are summed.
