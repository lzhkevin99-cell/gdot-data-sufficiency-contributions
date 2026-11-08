# Research directions (documented, not yet tested)

Both workstreams in this repo deal with the same underlying problem: **missingness**. The question is how
much a partial, gappy month of traffic data can be trusted, and how to still produce a usable estimate
when a station lacks enough clean data on its own. The main paper and the cluster-fallback MVP
([`cluster_fallback/`](cluster_fallback/)) both work by enlarging the reference pool. The ideas below
come at the problem from angles neither has tried.

Each idea comes from a specific gap between the paper and the EDA, not from first principles. None has
been tested yet. Each would need the same discipline used throughout this repo: keep observed results
separate from recommendations, and compare against a simple baseline before claiming anything.

## 1. Mechanism-conditional pooling
The paper already simulates six missingness mechanisms: MCAR, Block-1, Block-2, Weekday-heavy,
Weekend-heavy and Markov. Yet companion stations are selected the same way whichever mechanism is being
tested. A companion with strong overall correlation but weak *weekend* correlation is a poor backup
specifically under weekend-heavy missingness. The idea: screen or weight companions conditional on the
mechanism being evaluated, not once overall.

## 2. Outage co-occurrence as a *negative* signal
Today a "similar station" only means a similar traffic pattern. If a candidate companion's missing days
tend to coincide with the target's (a shared maintenance schedule, sensor vendor or district), it fails
exactly when it is needed. The EDA's outage classification
([`eda/eda_output/missingness/missingness_quality_report.md`](eda/eda_output/missingness/missingness_quality_report.md))
could screen candidates for *independent* outage timing, not just correlated traffic.

## 3. Impute-then-conform, not just pool-then-conform
Neither the paper nor the MVP fills small gaps before testing sufficiency. The EDA's corridor report
already recommends neighbor-based imputation
([`eda/eda_output/corridors/corridor_relationship_report.md`](eda/eda_output/corridors/corridor_relationship_report.md),
"Imputation design"). Running imputation *before* the conformal test changes the question from "are
*k* observed days enough?" to "are *k* observed plus imputed days enough?" That could rescue stations
with small, patchy gaps without needing a large reference pool at all, which makes it a different lever
from enlarging the pool.

## 4. Outage style as a stratification variable for k\*
The paper stratifies k\* by volume tier and functional class only. The EDA already assigns every
station an outage style (`always_on` / `occasional_gap` / `seasonal_dropout` / `chronic_sparse`).
Testing whether outage style predicts k\* better than volume tier is a cheap join between results that
already exist on both sides. A positive result could motivate a missingness-aware, not just
volume-aware, reporting rule.

## 5. Does the 2022–23 missingness spike threaten exchangeability?
The EDA found a missingness spike in 2022–23 (12.0% and 11.8%, against an 8.4% fleet average) that
coincides with a data-pipeline transition
([`eda/eda_output/missingness/fig_missingness_by_year.png`](eda/eda_output/missingness/fig_missingness_by_year.png),
[`eda/eda_output/reports/eda_roadmap.md`](eda/eda_output/reports/eda_roadmap.md)). Some stations' reference
pools may contain months from both sides of that structural break. For those stations, the conformal
procedure's exchangeability assumption may be quietly violated, but this EDA observation has not yet
been connected to a caveat in the paper.

## Rough effort
- **Quick** (existing outputs, mostly a join or rerun away): idea 4.
- **Medium** (a real new experiment, but bounded): ideas 2 and 5.
- **Bigger bet** (a new mechanism or design, more open-ended): ideas 1 and 3.
