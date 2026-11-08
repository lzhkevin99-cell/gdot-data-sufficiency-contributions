# Exploratory data analysis of the GDoT CCS network

A full EDA of the Georgia DOT continuous count station network (286 stations with data, 2017–2024),
done before any reference-pool or conformal modeling. It was run as a multi-agent AI pipeline:
seven analysis agents plus a synthesis agent. Its specification, [`claude.md`](claude.md), defines each
agent's scope, questions, deliverables and caveat requirements. See [`../README.md`](../README.md) for
how this fits with the cluster-fallback work.

## Which document to read

- **Presentation and reports** are in [`../deliverables/`](../deliverables/):
  - the [final slides](../deliverables/eda_final_slides.pdf);
  - the 14-page final report;
  - the pipeline-design document.
- **[`eda_output/reports/master_eda_summary.md`](eda_output/reports/master_eda_summary.md)** is the full
  synthesis across all agents. Start here for the numbers.
- [`eda_output/reports/executive_summary.md`](eda_output/reports/executive_summary.md) is a condensed
  top-findings version.
- [`eda_output/reports/eda_roadmap.md`](eda_output/reports/eda_roadmap.md) is forward-looking: open
  items, blockers, next steps.

## Two stages

- **`outputs/`** holds the raw Phase-1 ingestion produced by
  [`01_data_inventory.ipynb`](01_data_inventory.ipynb), which builds the station catalog (483 rows, 71
  raw TMAS columns), per-tier completeness audits and the 2024 event log. Only the notebook's figures
  are published here.
- **`eda_output/`** holds the agent pipeline's output, built from Phase 1, with one folder per agent.
  Each folder contains the agent script (`*_agent.py`), its figures, and its report:
  - `inventory/`: station master table (287 curated stations), completeness overview, schema audit
  - `missingness/`: missingness by station, month and year; outage-style classification
  - `profiles/`: baseline hourly, daily, weekly and monthly traffic patterns; archetypes
  - `trends/`: AADT trends, seasonality, holiday effects (2017–2024)
  - `corridors/`: pairwise station correlations, behavioral neighbors, reference-station candidates
  - `anomalies/`: anomaly detection, station-month trust tiers
  - `features/`: cleaned hourly dataset (sample) and feature specification for downstream modeling
  - `reports/`: the synthesis, plus the scripts that built the PDF reports and slide deck

## Reproducibility note

The agent scripts read the raw GDoT CCS archives (about 33 GB), using absolute paths from the machine
they ran on. Those archives are not distributed with this repository, so the scripts document the
method rather than being runnable here. Their reports and figures are committed.

**No data is published.** The data tables the agents produced (station tables, missingness
scorecards, trust tiers, correlation matrices, the clean hourly dataset) are derived from GDoT records
and stay local. The reports still refer to them by file name.

The deliverable PDFs now live in `../deliverables/`. The `build_*.py` scripts in
`eda_output/reports/` still write to their original `eda_output/reports/` location.
