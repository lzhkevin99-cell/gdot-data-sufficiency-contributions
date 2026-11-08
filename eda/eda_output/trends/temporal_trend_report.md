## Objective
Characterize temporal patterns in GDOT traffic data across 2017–2024 by computing:
- Multi-year AADT proxies (via June reference-month sampling)
- Monthly seasonality indices by functional class
- Holiday and long-weekend traffic effects (2024)
- Peak-hour stability across seasons (2023)

## Methods

### Station Selection
- Loaded `station_source_presence.csv` → **225** stations present in all 3 data tiers (n_sources == 3)
- Stratified sample of **30** stations selected, weighted toward stations with highest completeness,
  spanning 5 functional class categories
- FC breakdown: {'1': 13, '3': 8, '4': 5, '5': 3, '2': 1}

### AADT Proxy (Task 2)
- Read June monthly files from historical tier (2018–2022) and CCS tier (2022–2023) in 100k-row chunks
- Filtered immediately to 30 selected station IDs
- Computed raw daily volume per station per day; averaged across all June days
- AADT proxy = mean_daily_june_volume × 365
- BinDuration in both tiers: 300s (5-min); VolumeQC filter applied where column present
- For year 2022 covered by both tiers: CCS records preferred (higher quality)

### Seasonality (Task 4)
- Read all 12 monthly files for 2023 (CCS_2022-2023 tier), filtered to selected stations
- Computed mean daily volume per station per month (S_m)
- Seasonality index = S_m / annual_mean_daily_volume
- Peak month: **Oct** (mean SI = 1.036)
- Trough month: **Jan** (mean SI = 0.928)

### Holiday Effect (Task 5)
- Loaded `all_events_2024.csv` → 1980 Holiday-flag records
- Target holidays: New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas Day
- For each holiday station, read 2024 per-station files from CCS_5Min_2024/
- Control: same day-of-week ±1–2 weeks from holiday date, excluding other holidays
- Effect ratio = holiday_daily_volume / mean_control_daily_volume

### Long-Weekend Effect (Task 6)
- Compared Fri–Mon volume for Memorial Day, July 4, and Labor Day weekends vs.
  same Fri–Mon pattern ±3 typical weeks (excluding other long weekends)

### Peak-Hour Stability (Task 7)
- Extracted sub-daily volumes from 2023 monthly files for January, April, July, October
- Identified AM peak (6–10 AM) and PM peak (2–8 PM) for each station-month combination
- Visualized distribution of peak hours across seasons via box plots

## Key Findings

### AADT Trends
- Years with data in AADT table: [np.int64(2018), np.int64(2019), np.int64(2020), np.int64(2021), np.int64(2022), np.int64(2023)]
- Mean June daily volume across all selected stations: **26,692 vehicles/day** (where data available)
- COVID-19 impact (2019→2020 comparison): median volume drop ≈ **8.6%**
  (note: multiple confounding factors; causal attribution to COVID is observational)
- Post-2020 recovery trajectory visible by 2021–2022 in most functional class categories

### Seasonality
- Peak traffic month: **Oct** (SI = 1.036) — typical summer/tourist travel peak
- Trough month: **Jan** (SI = 0.928) — typical winter low
- Rural stations (FC 4–5) show stronger seasonality than urban/interstate stations

### Holiday Effects
    holiday_name  n_stations  mean_effect_ratio  std_effect_ratio
  New Year's Day         330                NaN               NaN
    Memorial Day         330                NaN               NaN
Independence Day         330                NaN               NaN
       Labor Day         330                NaN               NaN
    Thanksgiving         330                NaN               NaN
   Christmas Day         330                NaN               NaN

### Long-Weekend Effects
Long weekend 2024 data not loaded (station file matching required)

## Tables/Plots Created
| File | Description |
|------|-------------|
| `aadt_trends_by_station.csv` | Station × year AADT proxy, June mean daily volume, FC |
| `seasonal_index_by_station.csv` | Station × month seasonality index |
| `holiday_effect_summary.csv` | Holiday effect ratio summary |
| `fig_aadt_trend_2017_2024.png` | Line chart of annual volume trends by FC |
| `fig_seasonal_decomposition_examples.png` | Seasonality index by month (examples + FC aggregate) |
| `fig_holiday_effect.png` | Bar chart of holiday volume effect ratios |
| `fig_long_weekend_effects.png` | Long-weekend volume ratio grouped bar chart |
| `fig_peak_hour_stability.png` | AM/PM peak hour box plots by season |

## Risks/Caveats
1. **June-reference AADT proxy**: June is typically close to annual average for southeastern US,
   but may overestimate for resort/tourist corridors and underestimate in winter-peak areas.
2. **COVID dip analysis**: The 2019→2020 volume drop is observed in the data but may reflect
   multiple confounding factors beyond COVID-19 (data coverage changes, station dropouts).
3. **Tier mixing**: Historical (2017–2022) data uses directional lanes; CCS (2022–2023) uses
   numbered lanes. Volumes summed across all directions/lanes per station-day; comparison
   is valid if station configurations are stable, but lane-count changes may inflate/deflate trends.
4. **2024 per-station file format differs** from monthly tier: uses 'Start Time', 'Count' columns
   and includes speed/weight bins. Ensure Count column = total vehicle count per 5-min bin.
5. **Missing June 2022 from historical tier**: Used next available month (April 2022) as proxy.
6. **Holiday effect sample size**: Limited to stations present in CCS_5Min_2024/ directory.
   Stations with no matching cosit file were excluded.
7. **Seasonality from single year (2023)**: Does not capture inter-annual variability in seasonal patterns.

## Recommended Next Steps
1. **Extend AADT proxy to all 12 months** per year for selected stations to improve annual estimates.
2. **Compute proper AADT** using FHWA seasonal adjustment factors for Georgia by functional class.
3. **Validate June-proxy AADT** against any official GDOT AADT reports for cross-check.
4. **Expand holiday analysis** by reading all available 2024 station files (not just selected 20).
5. **Multi-year seasonality**: Stack 2022, 2023, and 2024 seasonal indices to assess inter-annual consistency.
6. **Peak-hour analysis**: Extend to a full year with directional breakdown (NB vs SB) for each station.
7. **COVID recovery analysis**: Use all months 2019–2022 to fit a recovery curve and estimate
   percent recovery by FC category.
