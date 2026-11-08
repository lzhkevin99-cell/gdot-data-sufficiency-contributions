# GDOT EDA Executive Summary

**Generated:** 2026-04-10
**Data window:** 2017–2024 | **Stations in catalog:** 330 | **Stations analyzed:** 286

---

## What Data Exists and How Much Is Usable

The GDOT CCS dataset spans three tiers: hourly directional data (2017–2022), 5-minute lane-level data (2022–2023), and 5-minute directional data with speed and weight bins (2024). Of 330 cataloged stations, **286 appear in at least one tier**; 225 (78.7%) appear in all three. Across 21,837 station-months, **91.6% are COMPLETE** (≥80% bin coverage), yielding an overall fleet missingness rate of 8.4%. At the station level, **243 stations (84.9%)** are rated HIGH trust and are ready for primary modeling use. An additional 36 CAUTION-tier stations may be used with caveats; 7 are excluded. The clean hourly 2024 dataset contains **818,645 records across 99 trusted stations** (26 columns, saved as CSV). A 286-station feature table with 27 columns is ready for AADT modeling.

---

## Top 5 Data Quality Findings

1. **Fleet is largely reliable:** 210 stations (73.4%) are "always_on" (≥90% complete months); only 5 stations (1.8%) are chronically sparse (<40% complete months).
2. **Structured missingness in 2022–2023:** Annual missingness spiked to 12.0%–11.8% during the 2022–2023 transition period — the highest since 2017 — consistent with pipeline migration from hourly directional to 5-minute lane-level collection. This pattern is not consistent with MCAR.
3. **Interstate/freeway stations have disproportionate missingness:** FC1 (Interstate) and FC2 (Freeways/Expressways) show 13.5% and 14.6% missingness respectively — the highest of any functional class — possibly reflecting methodology (more expected bins per multi-lane sensor) rather than true data quality failure.
4. **73 outage runs exceed 6 months** (out of 226 total outage sequences), with a maximum run of 60 consecutive absent months. These long outages likely represent sensor replacement cycles or extended decommissioning, not random gaps.
5. **6.48% of 2024 5-min bins** have Count=0 with Coverage >50% — potentially genuine zero-volume periods at rural overnight sites, but warrant review at urban/Interstate locations during peak hours.

---

## Top 5 Traffic Behavior Findings

1. **Median daily volume is 22,830 vehicles/day** across the 100-station 2024 sample; mean is 45,223/day (driven upward by high-volume freeway/expressway stations at ~110,000/day median).
2. **Peak hours are stable and consistent:** AM peak is 7:00; PM peak is 17:00 across functional classes and seasons — high confidence for use as fixed features in AADT models.
3. **Weekday/weekend ratio differs by functional class:** Interstates (1.08) are close to uniform 7-day use; arterials and collectors (1.35–1.44) carry meaningfully more weekday traffic, consistent with commuter orientation.
4. **Seasonality is modest (±10%):** October is the peak month (SI = 1.036); January the trough (SI = 0.928). Rural FC4–5 stations show stronger seasonality than urban/interstate stations.
5. **COVID-19 impact is visible but modest:** The 2019–2020 median volume drop was approximately 8.6% across the 30-station trend sample; recovery to near-2019 levels is observed by 2021–2022.

---

## Top 3 Risks for Modeling

1. **Holiday/event adjustment factors are unavailable.** The holiday effect analysis failed for all 6 major holidays due to a COSIT format mismatch between event records and 2024 per-station file naming. Any model relying on holiday-adjusted AADT or event-corrected counts cannot be finalized until this is fixed.
2. **Archetype stratification is not usable in current form.** k-means clustering (k=4) placed 77 of 78 classified stations into a single "Mixed" archetype. Models that depend on archetype-segmented behavior will require richer features (multi-year profiles, directional splits, vehicle class distributions) and likely a larger, more balanced sample.
3. **Correlation/imputation analysis covers only 80 of 230 eligible stations.** The 27 identified reference station candidates are drawn from the highest-completeness subset; stations ranked 81+ have not been assessed for corridor membership or behavioral neighbor suitability, leaving potential imputation donors unidentified.

---

## What Was Produced

| Output | Description |
|--------|-------------|
| `station_master_table.csv` | 286 stations × metadata + completeness + tier flags |
| `station_missingness_scorecard.csv` | Per-station outage style, completeness metrics |
| `station_daily_volume_summary.csv` | Per-station volume statistics (100-station sample) |
| `aadt_trends_by_station.csv` | Station × year AADT proxy (30-station, 2018–2023) |
| `reference_station_candidates.csv` | 27 top reference/imputation stations |
| `trusted_station_list.csv` | 243 HIGH-trust stations |
| `clean_hourly_2024_trusted.csv` | 818,645 hourly records, 99 stations, 26 columns |
| `station_feature_table.csv` | 286 stations × 27 modeling features |

---

## Recommended Next Steps

1. **Fix COSIT format mismatch** in the temporal trend and holiday analysis pipeline to enable holiday effect and long-weekend ratio computation.
2. **Remove the 100-station cap** in the feature pipeline to process all 207 trusted stations and expand the hourly dataset.
3. **Install pyarrow** and convert `clean_hourly_2024_trusted.csv` to Parquet for efficient large-dataset access.
4. **Expand corridor/correlation analysis** to the full 230-station eligible set with a relaxed min_periods threshold (e.g., 90 days) to identify additional behavioral neighbor pairs and imputation donors.
5. **Run AADT modeling** using `station_feature_table.csv` with functional_class, seasonal_amplitude, and pct_complete as primary predictors; validate against official GDOT AADT reports where available.
