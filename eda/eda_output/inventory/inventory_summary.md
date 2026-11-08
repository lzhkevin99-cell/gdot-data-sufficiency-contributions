## Objective

Build a unified station master table and produce inventory outputs for the GDOT traffic counting station dataset, covering three data tiers spanning 2017–2024. This supports the GDOT EDA workflow by characterising station coverage, data completeness, schema differences across tiers, and metadata quality.

---

## Methods

1. **station_catalog.csv** loaded as the canonical station list (330 rows, 330 unique COSIT values).
2. Three completeness CSVs unioned into a single long-format table keyed by station_id (station_name format `XXX-XXXX`).
3. Per-station aggregation: total months, complete months (where `complete == True`, equivalent to ≥80% bin coverage), first/last date.
4. station_source_presence.csv used for tier membership flags.
5. station_master_table built by joining presence + completeness data to catalog metadata via `station_name` ↔ `station_id` matching.
6. Schema audit performed by reading header + 5 rows from 3 sample CCS_5Min_2024 files, 1 GDOT_CCS_2022-2023 file, and 1 GDoT_UGA_Directional file.
7. Non-standard ID detection via regex matching against `^\d{3}-\d{4}$` pattern.
8. Five figures produced (functional class, urban/rural, source overlap, completeness distributions).

---

## Key Findings

### Station Counts
| Metric | Value |
|---|---|
| Rows in station_catalog | 330 |
| Unique COSIT values in catalog | 330 |
| Stations in master table | 286 |
| Stations matched to catalog metadata | 283 |
| Stations in all 3 tiers | 225 |
| Stations in exactly 2 tiers | 27 |
| Stations in exactly 1 tier | 34 |

### Completeness by Tier
```
                     mean  median  count
tier                                    
5min_2022_2023  95.384655   100.0   5385
5min_2024       96.649149   100.0   2585
hist_2017_2022  99.359181   100.0  13540
```

Complete month rates (completeness_pct >= 80%):
tier
5min_2022_2023    93.259053
5min_2024         94.893617
hist_2017_2022    98.759232

### Master Table Completeness Stats
- Mean complete months per station:   72.9
- Median complete months per station: 84.0

### Station ID Format Issues
| Metric | Count |
|---|---|
| Total IDs in source presence | 286 |
| Standard format (DDD-DDDD) | 284 |
| Non-standard IDs | 2 |
| IDs containing 'w' suffix | 2 |

Non-standard examples: `['021-w334', '185-w227']`

### Metadata Null Audit (top 10 columns by null %)
```
                              column  null_pct
                           Bridge ID 99.696970
  Micromobility Facility Type (TMAS) 99.696970
                      Recorder Model 99.393939
           TMAS Weighing Calibration 99.090909
         LTPP Site Id (TMAS 2001-16) 98.787879
                            End Desc 98.484848
                          Begin Desc 97.878788
      Weighing Method (TMAS 2001-16) 97.878788
Truck Weight Sample Type (TMAS 2001) 96.666667
Concurrent Route Signing (TMAS 2001) 96.363636
```

### Functional Class Distribution (top 8)
```
functional_class
1: Interstate                      139
3: Other Principal Arterial         77
4: Minor Arterial                   52
5: Major Collector                  34
2: Other Freeways / Expressways     23
7: Local Access                      3
6: Minor Collector                   2
```

### Urban/Rural Breakdown
```
fc_urban_rural
1U: Urban Interstate                      115
3U: Urban Other Principal Arterial         52
4U: Urban Minor Arterial                   38
3R: Rural Other Principal Arterial         25
1R: Rural Interstate                       24
2U: Urban Other Freeways / Expressways     23
5U: Urban Major Collector                  19
5R: Rural Major Collector                  15
4R: Rural Minor Arterial                   14
7U: Urban Local Access                      3
6U: Urban Minor Collector                   2
```

### Schema Key Differences Across Tiers
| Dimension | Tier 1: CCS_5Min_2024 | Tier 2: GDOT_CCS_2022-2023 | Tier 3: GDoT_UGA_Directional_2017-2022 |
|---|---|---|---|
| Station ID | 12-digit COSIT in filename | 'Site' col, `XXX-XXXX` | 'Site' col, `XXX-XXXX` |
| Time column | 'Start Time' | 'Time' | 'Time' |
| Resolution | 5-min (implied) | 5-min (BinDuration=300) | Hourly (BinDuration=3600) |
| Stratification | Direction (N/S/E/W) | Lane (Ln 1 NB etc.) | Direction (N/S/E/W) |
| Speed data | Speed bins (<10 mph…>80 mph) | None | AvgSpeed only |
| Weight data | Weight bins present | None | None |
| QC flags | Coverage % per interval | None in monthly files | VolumeQC, ClassQC |

---

## Tables/Plots Created

| File | Description |
|---|---|
| `station_master_table.csv` | One row per station with metadata + completeness + tier flags |
| `schema_audit_notes.txt` | Detailed schema comparison across all 3 tiers |
| `fig_functional_class.png` | Bar chart of station counts by FHWA functional class |
| `fig_urban_rural.png` | Pie chart of urban vs. rural station distribution |
| `fig_data_source_overlap.png` | Bar chart of station counts by source tier combination |
| `fig_completeness_distribution.png` | Histograms of monthly completeness % per tier |

---

## Risks/Caveats

1. **ID format mismatch**: Tier 1 (2024) uses 12-digit zero-padded numeric COSIT in filenames (`000000010183`), while Tiers 2 & 3 and the completeness CSVs use the `XXX-XXXX` station_name format (`001-0183`). A derivation mapping is applied (padding/unpadding), but edge cases may exist for non-standard IDs.

2. **Non-standard IDs**: 2 station IDs do not match the `DDD-DDDD` pattern. These may be legacy, WIM, or special-purpose sites. They cannot be reliably cross-referenced without additional lookup tables.

3. **completeness_2024.csv has COSIT column; others have station_name**: The completeness union normalises on station_name format, but the Tier 1 completeness table reports `cosit` as the primary key. Mismatches could cause ~3 stations to appear with incomplete catalog metadata.

4. **Multiple data files per station in 2024**: Some stations have `data-2.csv`, `data-3.csv`, etc. (possibly from recorder replacements or multi-sensor setups). The completeness metrics may not capture all sub-files.

5. **High null rates in catalog**: Several metadata columns (e.g., Bridge ID, LTPP Site Id, WIM fields) have very high null rates because they are only applicable to specific station types. These are not data quality issues per se.

6. **Hourly vs. 5-minute resolution**: Tier 3 data (2017-2022) is hourly, making direct bin-count comparisons with Tiers 1 & 2 inappropriate without resampling.

---

## Recommended Next Steps

1. **Reconcile the COSIT ↔ station_name mapping** systematically: build a definitive lookup table from `station_catalog.csv` (`cosit` → `station_name`) and apply it as the canonical join key across all tiers.

2. **Investigate non-standard station IDs** (n=2): determine if 'w'-suffixed IDs correspond to WIM stations or legacy codes; add a `station_type` flag to the master table.

3. **Gap-fill analysis**: for stations with incomplete months (particularly in Tier 3), determine whether gaps are systematic (sensor failure, seasonal shutdown) or random — this is prerequisite for imputation modelling.

4. **Multi-file stations in 2024**: audit which stations have `data-2.csv` or higher and verify the completeness calculation in `01_data_inventory.ipynb` correctly aggregates across all data files.

5. **Schema harmonisation**: design a unified intermediate schema (Site, Time, Direction, Volume, F1-F15, BinDuration_sec, AvgSpeed, Coverage_pct) that can accommodate all three tiers, enabling longitudinal analysis.

6. **Functional class QA**: cross-check `functional_class` values in the catalog against HPMS/FHWA definitions; flag any stations where `functional_class` is null (see null audit table).

7. **Completeness thresholding sensitivity**: the 80% threshold is hardcoded in the existing pipeline. Evaluate whether different thresholds (e.g., 70%, 90%) materially change which station-months are flagged as usable.
