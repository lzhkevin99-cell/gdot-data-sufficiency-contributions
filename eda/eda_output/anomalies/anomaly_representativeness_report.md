## Objective

Detect anomalous daily volumes at 2024 GDOT traffic count stations, cross-check detected anomalies against known event flags, and assign trustworthiness tiers to each station-month and station. Outputs support downstream decisions about which station-months are suitable for traffic modeling.

## Methods

### Station Selection (Task 1)
- Universe: 286 stations in station_master_table.
- Eligibility criteria: in_5min_2024 == True AND pct_complete > 0.70 (from missingness scorecard).
- Stratified sample of 60 stations across functional classes, proportional to FC representation.
- 58 of the 60 sampled stations had readable raw 5-min data files.

### Anomaly Detection (Task 1)
For each station with raw data:
- Aggregated 5-min intervals to daily totals, filtering intervals with Coverage % < 50.
- Computed station-level median and IQR (Q75 - Q25) over all observed days.
- Flagged anomaly days using two criteria:
  1. IQR rule: daily_volume < (median − 3×IQR) OR > (median + 3×IQR)
  2. Low-volume rule: daily_volume < 10% of median (consistent with potential sensor dropout when coverage is otherwise high)

### Event Cross-Check (Task 2)
- Loaded 15961 event flags from all_events_2024.csv.
- Matched flagged anomaly days to events of type: Holiday, Volume Bad, Volume Outlier, Volume Atypical, Roadworks, Road Closure, Accident.
- Classification: EXPLAINED (overlap found) vs UNEXPLAINED (no matching event).

### Trustworthiness Scoring (Task 3)
- For the 58 stations with raw data: used coverage_pct + unexplained anomaly count to assign TRUSTED / CAUTION / EXCLUDE per station-month.
- For remaining stations: used quality_flag from station_month_issue_table as proxy (COMPLETE → TRUSTED; PARTIAL_MINOR / PARTIAL_MAJOR → CAUTION; SPARSE / ABSENT → EXCLUDE).

### Station Aggregation (Tasks 4–5)
- Summarised station-month tiers into pct_trusted per station → HIGH / MODERATE / LOW station trust tier.
- Applied additional criteria for station lists: n_sources ≥ 2 and n_trusted_months ≥ 8 for TRUSTED list; n_trusted_months < 3 or tier == LOW for EXCLUDED list.

## Key Findings

### Anomaly Detection
- Total anomaly-days detected across 58 stations: **391**
- Explained by event flags: **354** (90.5%)
- Unexplained anomaly-days: **37** (9.5%)
- Note: "Unexplained" does not imply the data is wrong — it means no corresponding event flag exists in the available event log. Zero-volume overnight periods at rural stations are not flagged because the IQR-based method naturally accommodates station-typical patterns.

### Station-Month Trustworthiness
| Tier    | Station-Months | % of Total |
|---------|---------------|------------|
| TRUSTED |        19,963 | 96.9% |
| CAUTION |           233 | 1.1% |
| EXCLUDE |           404 | 2.0% |
| **Total** |        20,600 | 100.0% |

### Station-Level Trust Summary
| Tier     | Stations |
|----------|----------|
| TRUSTED  |      243 |
| CAUTION  |       36 |
| EXCLUDED |        7 |

## Tables/Plots Created

| File | Description |
|------|-------------|
| `anomaly_log.csv` | Per-anomaly-day record: station, date, volume, thresholds, event flag, explained flag |
| `station_month_trustworthiness.csv` | Per station-month: coverage, quality flag, anomaly counts, trust tier, method |
| `station_trust_summary.csv` | Per station: n trusted/caution/exclude months, pct_trusted, station trust tier |
| `trusted_station_list.csv` | 243 stations rated HIGH trust with ≥2 sources and ≥8 trusted months |
| `caution_station_list.csv` | 36 stations suitable for use with caveats |
| `excluded_station_list.csv` | 7 stations flagged for investigation or exclusion |
| `fig_trust_tier_distribution.png` | Stacked bar chart of station-month trust tiers by functional class |
| `fig_anomaly_timeline.png` | Daily volume time series for 4 example stations with anomaly and event markers |
| `fig_volume_anomaly_examples.png` | 2×2 histogram grid with IQR and low-volume thresholds |

## Risks/Caveats

1. **Coverage proxy limitation**: The majority of stations were scored using quality_flag (coverage proxy) rather than raw data inspection. The proxy cannot detect volume-level anomalies — only data presence.
2. **IQR sensitivity**: The 3×IQR rule is robust but may miss sustained gradual drift. Stations with highly variable demand (e.g., near event venues) may have inflated IQR, reducing anomaly detection sensitivity.
3. **Unexplained anomalies**: 37 anomaly-days have no event flag. These may reflect: (a) genuine sensor issues, (b) events not recorded in the event log, (c) legitimate unusual traffic (e.g., incidents not captured, detours). These are not classified as erroneous without further investigation.
4. **Low-volume rule**: Flagging days with volume < 10% of median as "consistent with sensor failure" is heuristic. For rural overnight stations, median may already be near zero — the per-station threshold mitigates this but does not eliminate it.
5. **Sample size**: Only 58 stations had raw data read. Stations not in the sample rely on the coverage proxy, which may underestimate anomaly risk.
6. **Single-direction data**: data-1.csv captures one primary direction; multi-directional anomalies may be missed.

## Recommended Next Steps

1. **Investigate unexplained anomalies**: Pull the 37 unexplained anomaly-days and audit against maintenance logs, weather records, and construction permit databases.
2. **Expand raw-data coverage**: Run the IQR anomaly check on all in_5min_2024 stations (not just the 60-station sample) to reduce reliance on the coverage proxy.
3. **Refine the low-volume threshold**: Consider a tiered threshold (e.g., 5% for rural, 15% for urban interstate) to reduce false positives at low-volume rural sites.
4. **Cross-validate with Phase 3A profiles**: Compare anomaly-day volumes with the F-class distribution profiles from Phase 3A to determine whether anomaly days skew toward atypical vehicle mixes.
5. **Flag CAUTION stations for sensitivity testing**: In downstream modeling, run models with and without CAUTION-tier station-months to quantify their influence on estimates.
6. **Revisit EXCLUDED stations**: Some may be recoverable with partial-month data after dropping specific anomaly intervals.
