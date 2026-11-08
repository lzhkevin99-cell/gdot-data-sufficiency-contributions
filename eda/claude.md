# CLAUDE.md

## Project Goal

Your primary objective is to perform an exhaustive Exploratory Data Analysis (EDA) of the GDOT traffic dataset so that we become true **data experts** before any modeling begins.

This is not just a plotting exercise. The goal is to deeply understand:

- what data exists
- how the dataset is structured
- which parts are reliable vs unreliable
- what normal traffic patterns look like
- how patterns vary across stations, months, years, and corridors
- how missingness behaves
- how stations relate to one another
- what cleaned, analysis-ready data should be produced for future modeling

You should use subagents when useful to divide work into clear analysis tracks. Be creative, thorough, and organized. The EDA should show a complete understanding of the dataset.

---

## Core Principles

1. **Become data experts first**
   - Do not rush into modeling.
   - First understand the dataset at the station, month, year, and corridor level.

2. **Be exhaustive but structured**
   - Cover both manager-suggested EDA ideas and additional useful analyses.
   - Organize findings clearly by theme.

3. **Be evidence-based**
   - Do not overclaim.
   - If a conclusion is uncertain, say so.
   - Especially for missingness classification, use cautious language such as:
     - "consistent with MCAR"
     - "suggests structured missingness"
     - "bursty outage pattern"
   - Do not claim MAR/MCAR definitively unless the evidence truly supports it.

4. **Think like both a data scientist and a traffic analyst**
   - We care about data quality, temporal patterns, traffic behavior, inter-station relationships, and future model-readiness.

5. **Produce reusable outputs**
   - Save tables, plots, summaries, and cleaned datasets in a reproducible way.
   - Write code that can scale across stations, not just one-off scripts.

---

## Overall EDA Questions To Answer

The EDA should help answer the following:

### Data inventory and structure
- How many stations are in the dataset?
- What years and months are available for each station?
- How many complete vs incomplete months does each station have?
- What metadata is available?
- How are stations distributed across functional classes and urban/rural categories?
- Are schemas consistent across years and files?

### Missingness and data quality
- What percentage of data is missing by station?
- Which stations or months are incomplete?
- What does missingness look like over time?
- Are missing gaps random, block-like, weekday-heavy, weekend-heavy, or bursty?
- Is there hour-of-day or day-of-week bias in missingness?
- Are there zero-volume intervals, low-coverage intervals, or impossible records?
- Can we identify likely sensor failures or event-driven disruptions?

### Baseline traffic behavior
- What does normal traffic look like at each station?
- What are the daily volume distributions?
- What are the typical hourly, day-of-week, and monthly traffic profiles?
- How do weekday and weekend patterns differ?
- What are the speed, class, length, and weight profiles where available?
- What are the AM and PM peak structures?

### Temporal dynamics
- How does traffic evolve across years?
- What are the AADT trends?
- What are the year-over-year monthly changes?
- Do weekday/weekend ratios drift over time?
- How strong are seasonal effects?
- What do STL or similar decompositions show?
- How do holidays and long weekends affect traffic?
- Is peak-hour behavior stable across years?

### Inter-station and corridor relationships
- Which stations behave similarly?
- What are the pairwise correlations by month?
- Do traffic patterns propagate along corridors?
- Does correlation decay with distance?
- Are some stations better reference stations than others?
- Are behavioral neighbors different from simply geographic neighbors?

### Anomalies and representativeness
- Which days or intervals look anomalous?
- Are anomalies likely sensor errors or real traffic events?
- Which station-months are trustworthy?
- When a month is incomplete, is it still representative?
- How many observed days are enough under different outage structures?

### Modeling readiness
- What aggregation level is best: 5-minute, 15-minute, hourly, or daily?
- What features should be engineered for future modeling?
- What cleaned analysis-ready datasets should be produced?
- What risks or leakage issues should be documented?

---

## Recommended Subagent Workflow

Use subagents when appropriate. A good workflow is:

### 1. `station_inventory_agent`
Focus:
- total number of stations
- total station-years and station-months
- metadata completeness
- functional class distribution
- urban/rural breakdown
- complete vs incomplete months
- schema consistency

Deliverables:
- station master table
- completeness table
- metadata summary
- schema/data dictionary audit

---

### 2. `missingness_quality_agent`
Focus:
- percent missing by station, month, hour, and day of week
- station × date missingness heatmaps
- run-length distribution of missing days
- complete vs incomplete months
- zero-volume intervals
- low-coverage intervals
- impossible records
- likely sensor failures
- candidate outage labels:
  - random
  - single block
  - two-block
  - weekday-heavy
  - weekend-heavy
  - bursty/intermittent

Important:
- Be cautious when discussing MCAR/MAR.
- Describe what patterns are consistent with the data rather than making unsupported causal claims.

Deliverables:
- missingness scorecards
- issue taxonomy
- outage pattern summary
- flagged data-quality windows

---

### 3. `traffic_profile_agent`
Focus:
- daily volume distributions by station
- hourly volume profiles
- day-of-week profiles
- monthly/seasonal profiles
- weekday vs weekend comparisons
- direction-level comparisons where applicable
- vehicle mix distributions
- speed, length, and weight distributions where available
- AM/PM peak identification
- station archetypes

Deliverables:
- station profile plots
- healthy traffic signature summaries
- station archetype notes
- core descriptive statistics tables

---

### 4. `temporal_trend_agent`
Focus:
- annual average daily traffic (AADT) trends by station
- year-over-year monthly volume changes
- seasonal decomposition (STL or similar)
- weekday/weekend ratio drift
- holiday and long-weekend effects
- day-of-week × month interaction heatmaps
- AM/PM peak ratio stability
- peak hour factor stability across years

Deliverables:
- trend summary tables
- decomposition plots
- seasonality summaries
- holiday effect analyses

---

### 5. `corridor_relationship_agent`
Focus:
- pairwise Pearson correlation matrices by month
- scatter plots for station-pair daily volumes
- lead/lag cross-correlation between stations
- distance-vs-correlation relationships
- clustering of stations by temporal profile
- identification of behavioral neighbors
- same-corridor vs nearby-but-mismatched comparisons

Deliverables:
- pairwise correlation matrices
- corridor relationship memo
- behavioral neighbor table
- reference-station candidates

---

### 6. `anomaly_representativeness_agent`
Focus:
- anomaly detection using rolling median + MAD
- anomaly detection using daily IQR-based rules
- persistent abnormal windows
- separation of sensor-error-like anomalies vs likely real-world events
- event impact summaries
- representativeness of incomplete station-months
- observed-day sufficiency under different outage structures

Deliverables:
- anomaly tables
- anomaly plots
- event impact summaries
- station-month representativeness table:
  - representative
  - review
  - insufficient

---

### 7. `feature_pipeline_agent`
Focus:
- compare 5-minute, 15-minute, hourly, and daily aggregations
- recommend best resolution for downstream analysis
- engineer temporal features
- create event flags
- create lag and rolling features
- create composition features such as truck share, heavy vehicle share, speed-band shares
- create corridor-relative or station-relative features where useful
- document all preprocessing choices

Deliverables:
- clean aggregated datasets
- feature specification document
- reusable preprocessing pipeline
- modeling-ready tables

---

### 8. `eda_manager_agent`
Focus:
- synthesize all subagent outputs
- resolve contradictions
- identify strongest findings
- identify risks and caveats
- propose next steps

Deliverables:
- master EDA report
- top findings summary
- trusted stations/months list
- caution list
- recommended next modeling steps

---

## Required EDA Coverage

At minimum, the EDA should include the following.

### A. Basic data quality and structure
- total number of stations
- missing data audit: % missing by station
- count of complete vs incomplete months per station
- distribution of functional classes
- urban/rural stratification
- row counts by station-year-month
- schema consistency checks

### B. Univariate distributions
- daily volume distribution per station
- hourly volume profile
- day-of-week volume profile
- monthly volume profile
- weekday vs weekend comparisons
- relevant distribution summaries for speed, class, length, and weight bins

### C. Temporal trends
- AADT trend by year per station
- year-over-year monthly volume change
- weekday vs weekend ratio drift
- long-weekend / holiday effect
- decomposition: trend + seasonality + residual
- AM/PM peak stability
- peak hour factor stability

### D. Inter-station relationships
- pairwise Pearson correlation matrix by month
- station A vs station B daily scatter plots
- lead/lag cross-correlation
- distance-vs-correlation curve
- station clustering or behavioral-neighbor analysis

### E. Missingness characterization
- station × date missingness heatmaps
- run-length distribution of consecutive missing days
- hour-of-day bias in missingness
- day-of-week bias in missingness
- classify outage style where possible
- discuss whether missingness appears random or structured

### F. Volume pattern and anomaly analysis
- anomaly detection using robust methods
- daily outlier flags
- month × day-of-week interaction heatmaps
- event impact summaries
- identify unusual station-months or periods

### G. Modeling-readiness
- recommended aggregation level
- cleaned analysis-ready datasets
- documented preprocessing rules
- feature engineering summary
- train/validation considerations and caveats

---

## How To Execute The Work

### Step 1: Build the data inventory
Start by understanding all files, tables, metadata, station IDs, directions, years, and coverage.

### Step 2: Audit completeness and missingness
Before deep pattern analysis, quantify what is missing and how missingness behaves.

### Step 3: Understand normal traffic behavior
Build baseline hourly, daily, weekly, and monthly traffic profiles.

### Step 4: Study time evolution
Analyze trends, seasonality, drift, and event effects.

### Step 5: Study spatial and corridor relationships
Understand how stations relate to each other and which stations are good comparators.

### Step 6: Identify anomalies and assess trustworthiness
Flag suspicious periods and determine which station-months are reliable enough for future use.

### Step 7: Produce clean modeling-ready outputs
Create reproducible cleaned datasets and engineered features.

### Step 8: Synthesize all findings
Write one clear master EDA summary.

---

## Output Expectations

Every subagent should return results in the following format:

### Objective
What this subagent was trying to answer.

### Methods
What computations, summaries, tests, and plots were used.

### Key Findings
What was learned.

### Tables / Plots Created
List important outputs.

### Risks / Caveats
What remains uncertain, limited, or potentially biased.

### Recommended Next Steps
What should happen after this analysis.

---

## Code Quality Expectations

- Write clear, modular, reusable code.
- Avoid hardcoding for a single station unless explicitly doing a case study.
- Use functions and pipelines where possible.
- Save outputs in an organized folder structure.
- Make results reproducible.
- Prefer readable code over clever code.
- Document assumptions.

Suggested output folders:

- `eda_output/inventory/`
- `eda_output/missingness/`
- `eda_output/profiles/`
- `eda_output/trends/`
- `eda_output/corridors/`
- `eda_output/anomalies/`
- `eda_output/features/`
- `eda_output/reports/`

---

## Important Analytical Cautions

1. **Missingness mechanism**
   - Do not casually label data as MCAR, MAR, or MNAR.
   - These are strong claims.
   - Use descriptive evidence first.

2. **Correlation is not causation**
   - Especially for inter-station relationships and lead/lag analysis.

3. **Sensor failure vs real-world event**
   - Distinguish technical issues from genuine traffic disruptions where possible.

4. **Different years may have different schema richness**
   - Be careful when comparing across years if fields changed.

5. **Complete does not always mean trustworthy**
   - A month can be complete but still contain abnormal events or bad sensor behavior.

6. **Partial does not always mean unusable**
   - Some incomplete months may still be representative.

---

## Final Deliverables

The final output should include:

1. **Master EDA report**
   - clear summary of the dataset
   - major findings
   - key risks
   - recommended next steps

2. **Station master table**
   - station metadata
   - coverage/completeness metrics

3. **Data quality report**
   - missingness and issue summaries

4. **Traffic behavior report**
   - baseline patterns and temporal trends

5. **Inter-station relationship report**
   - corridor and comparator insights

6. **Anomaly and representativeness report**
   - flagged periods and trustworthiness assessment

7. **Clean analysis-ready datasets**
   - aggregated and filtered appropriately

8. **Feature specification document**
   - engineered features and preprocessing decisions

---


## Final Instruction

Be proactive, organized, and thorough. The goal is to leave this stage with a deep, credible, and reusable understanding of the GDOT dataset. The final EDA should make it obvious that we understand the data well enough to justify whatever modeling choices come next.