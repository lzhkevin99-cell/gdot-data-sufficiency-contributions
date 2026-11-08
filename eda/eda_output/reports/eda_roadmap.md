# EDA to Modeling Roadmap

**Generated:** 2026-04-10
**Status:** EDA Phase 5 complete — all 7 agents finished

---

## Immediate Next Steps (before any modeling)

These items must be resolved before modeling outputs can be considered reliable:

### 1. Fix COSIT Format Mismatch (blocking — holiday/event analysis)
- **Problem:** The holiday effect and long-weekend analysis failed for all 6 major holidays because the 2024 per-station file naming uses a 12-digit COSIT format, while the event flags in `all_events_2024.csv` use the `XXX-XXXX` station_name format. Effect ratios returned NaN for all 330 stations across all holidays.
- **Fix:** Build a canonical `cosit → station_name` lookup table from `station_catalog.csv` and apply it as the join key in the temporal trend agent before loading per-station files.
- **Impact:** Unblocks holiday adjustment factors, long-weekend volume ratios, and event-corrected AADT estimates.

### 2. Remove 100-Station Pipeline Cap (blocking — hourly dataset coverage)
- **Problem:** The feature pipeline capped hourly data processing at 100 stations despite 207 trusted stations being eligible (207 with ≥6 trusted 2024 months meeting in_5min_2024 = True). Current hourly dataset covers only 48% of the eligible trusted population.
- **Fix:** Remove the cap and re-run the hourly aggregation pipeline. Estimate ~200MB CSV output for 207 stations; install pyarrow first to write Parquet (~40MB) instead.
- **Impact:** Enables full-population AADT modeling and gap-filling rather than a sampled subset.

### 3. Install pyarrow and Convert to Parquet
- **Problem:** pyarrow was not installed; clean hourly data was saved as a 104MB CSV (99 stations). At full scale (207 stations), the CSV would be approximately 218MB and significantly slower to load.
- **Fix:** `pip install pyarrow` and re-run the feature pipeline with Parquet output enabled.
- **Impact:** Reduces storage by ~75% and dramatically improves I/O performance for downstream modeling scripts.

### 4. Expand Corridor Analysis to Full Station Set
- **Problem:** The correlation matrix and reference station candidates were derived from only the top 80 stations by completeness. 150 additional eligible stations (in_5min_2024=True, n_sources≥2) have not been assessed for behavioral neighbor relationships or corridor cluster membership.
- **Fix:** Re-run corridor agent with all 230 eligible stations, using a relaxed min_periods threshold of 90 overlapping days (down from 180) to capture pairs with seasonal outages.
- **Impact:** May identify additional imputation donors and expand the 27-candidate reference station pool.

### 5. Investigate the 5 Chronic-Sparse Stations
- **Problem:** 5 stations (including 021-0349 and 021-0372) have fewer than 40% complete months across their operational history. Their status — decommissioned, relocated, or persistently failing — is unknown.
- **Fix:** Cross-reference these stations against GDOT event logs and field maintenance records. Flag for exclusion from longitudinal trend analysis pending investigation.

### 6. Resolve Non-Standard Station IDs
- **Problem:** 2 stations (`021-w334`, `185-w227`) use 'w'-suffix IDs that do not match the standard `DDD-DDDD` format and cannot be reliably joined across tiers without an additional lookup.
- **Fix:** Determine whether these are WIM (weigh-in-motion) stations or legacy codes; add a `station_type` flag to the master table.

---

## Recommended Modeling Approach

### Phase A — AADT Estimation
- **Input:** `station_feature_table.csv` (286 stations × 27 features)
- **Approach:** Regression model (e.g., gradient boosting or linear with interaction terms) using `functional_class`, `fc_urban_rural`, `seasonal_amplitude`, `pct_complete`, and `n_sources` as predictors for `aadt_2024_estimate`.
- **Validation:** Cross-validate against official GDOT AADT reports for stations with known ground-truth counts. Use the 27 reference station candidates as holdout validation points.
- **Caveat:** `aadt_2024_estimate = median_daily_volume × 365` is a June-independent proxy; apply seasonal adjustment factors (from `seasonal_index_by_station.csv`) to improve accuracy for high-amplitude stations (seasonal_amplitude > 0.4).

### Phase B — Gap Filling / Imputation
- **Input:** `clean_hourly_2024_trusted.csv`, `behavioral_neighbor_table.csv`, `reference_station_candidates.csv`
- **Approach:** For each station-hour with missing data, identify behavioral neighbors (r > 0.7, distance < 50 km) from the neighbor table. Apply ratio-based or k-NN imputation using reference station candidates as first-choice donors.
- **Priority stations for imputation:** The 36 CAUTION-tier stations and the 26 seasonal_dropout stations that may have sufficient partial-year data to recover full-year estimates.
- **Validation:** Mask known-good periods in trusted stations and measure imputation accuracy (MAPE, bias) by functional class.

### Phase C — Anomaly-Adjusted Counts
- **Input:** `anomaly_log.csv`, `station_month_trustworthiness.csv`, event flags from `all_events_2024.csv`
- **Approach:** For model training, exclude anomaly-days flagged as UNEXPLAINED (37 days, 9.5% of detected anomalies). For CAUTION-tier station-months (233 total), run sensitivity tests with and without these observations to quantify their influence.
- **Note:** Holiday and long-weekend adjustment requires the COSIT fix (Immediate Next Step 1) before proceeding.

### Phase D — Archetype Modeling (deferred)
- **Current status:** k-means (k=4) produced poor separation — 77/78 stations labeled "Mixed." Archetype modeling cannot proceed meaningfully with current features.
- **Requirements before proceeding:** Multi-year daily profiles (2019–2023), directional NB/SB split features, vehicle class fractions from Tier 1 speed/weight bins, and a larger sample (all 207 trusted stations rather than 100).
- **Recommended approach once data is available:** Hierarchical clustering on normalized multi-year seasonal profiles, validated against land-use data and FHWA functional class expectations.

---

## Known Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Holiday effects unquantified due to COSIT mismatch | High | Fix COSIT lookup (Immediate Step 1); re-run temporal trend agent |
| Archetype labels collapse to "Mixed" for 99% of stations | High | Defer archetype modeling; use functional_class as primary stratifier |
| Corridor analysis based on 80/230 eligible stations | Medium | Re-run with full station set after cap removal (Immediate Step 4) |
| Hourly dataset covers only 99 of 207 trusted stations | Medium | Remove 100-station cap (Immediate Step 2) |
| 2022–2023 missingness spike may bias longitudinal models | Medium | Flag 2022–2023 station-months with elevated missingness; run models with and without flagged period |
| Interstate/freeway missingness may reflect methodology not data quality | Medium | Validate expected-bin calculation for multi-lane sensors; apply FC-specific completeness thresholds |
| 37 unexplained anomaly-days may inflate or deflate training signal | Low | Exclude from model training; audit against weather/incident records |
| Non-standard IDs (`021-w334`, `185-w227`) may cause join failures | Low | Build explicit COSIT lookup; add station_type flag |
| Tier 3 (2017–2022) hourly vs. Tier 1/2 5-min resolution mismatch | Low | Resample Tier 3 to hourly before any cross-tier volume comparison |

---

## Open Questions Requiring Investigation

1. **What caused the 2022–2023 missingness spike?**
   Was the 12%+ missingness rate in 2022–2023 driven by specific GDOT districts, a particular functional class, or pipeline transition artifacts? Cross-referencing with field maintenance logs is needed to distinguish sensor attrition from reporting gaps.

2. **Are Interstate missingness rates a methodology artifact?**
   FC1 and FC2 stations show 13–15% missingness — the highest in the fleet. The 80% threshold may be harder to achieve for multi-lane sensors with more expected bins. Validate the expected-bin calculation before concluding that Interstate data is structurally lower quality.

3. **What is the status of the 5 chronic-sparse stations?**
   Stations with <40% complete months (including 021-0349 and 021-0372) need explicit investigation. Are they decommissioned? Relocated? Can partial data still support seasonal index estimation?

4. **Can the 36 CAUTION-tier stations be salvaged for modeling?**
   These stations have moderate data quality (70–90% complete months or low unexplained anomaly counts). Sensitivity testing (models with vs. without CAUTION stations) would clarify whether their inclusion materially changes AADT estimates or trend slopes.

5. **Do the 7 corridor clusters correspond to physical road segments?**
   The 7 multi-station behavioral clusters were identified purely from temporal volume co-movement, without road-network topology. Cross-referencing with GDOT route IDs or GIS shapefiles would confirm whether clusters represent actual corridors (e.g., I-285, I-75) and improve imputation donor selection.

6. **How stable are seasonal indices across years?**
   The 2023 seasonal index (October peak SI = 1.036, January trough = 0.928) is based on a single year. Stacking 2022–2024 indices would reveal whether inter-annual variability is large enough to affect seasonal AADT adjustment factors.

7. **What explains the 37 unexplained anomaly-days?**
   These days have no matching event flag. Weather events, unlogged incidents, or sensor drift are plausible causes. Auditing against NOAA weather records and GDOT construction permit databases would clarify classification.
