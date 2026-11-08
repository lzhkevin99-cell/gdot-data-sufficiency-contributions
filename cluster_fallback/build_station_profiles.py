"""Build station traffic-pattern profiles + missingness report for clustering.

This is personal/experimental work living outside the paper's `code/` tree --
it reads the paper's existing data (`code/data/`, `code/cache/`) read-only and
never edits anything under `code/`. Run from this `cluster_fallback/` directory:

    python build_station_profiles.py --month 4

Writes to cluster_fallback/clustering/output/:
    profiles_{tag}.parquet          one row per included station (raw + shape 7-vectors)
    missingness_by_station_{tag}.csv
    missingness_by_year_{tag}.csv
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from clustering.paths import CODE_DIR, PROJECT_ROOT  # set GDOT_PROJECT_ROOT; see clustering/paths.py
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)  # so `from modules import ...` / `import run_multi_site` resolve

import pandas as pd

from clustering import missingness as ms
from clustering import profiles as pf
from clustering import interpret as it

DATA_DIR = os.path.join(CODE_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "clustering", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("build_station_profiles")


def main(target_month: int = 4, tag: str = "apr"):
    cm_all = pd.read_parquet(os.path.join(DATA_DIR, "complete_months_all.parquet"))
    log.info(f"Loaded {len(cm_all)} complete months, {cm_all['site'].nunique()} sites")

    fv = ms.load_full_daily()
    fvd = ms.collapse_directions(fv)
    log.info(f"Daily inventory: {len(fv)} raw rows -> {len(fvd)} (site,date) rows after direction collapse")

    missingness = ms.missingness_report(fvd, target_month=target_month)
    by_station, by_year = missingness["by_station"], missingness["by_year"]
    log.info(f"Missingness computed for {len(by_station)} sites with any month-{target_month} history")

    profiles_df = pf.build_station_profiles(cm_all, target_month=target_month, completeness=by_station)
    profiles_df = it.add_volume_tier(profiles_df)
    n_included = int(profiles_df["included"].sum())
    n_excluded = len(profiles_df) - n_included
    log.info(
        f"Profiles built for {len(profiles_df)} sites with >=1 complete month-{target_month}; "
        f"{n_included} pass completeness>= {pf.PROFILE_COMPLETENESS_MIN} gate, {n_excluded} excluded"
    )

    profiles_df.to_parquet(os.path.join(OUTPUT_DIR, f"profiles_{tag}.parquet"), index=False)
    by_station.to_csv(os.path.join(OUTPUT_DIR, f"missingness_by_station_{tag}.csv"), index=False)
    by_year.to_csv(os.path.join(OUTPUT_DIR, f"missingness_by_year_{tag}.csv"), index=False)
    log.info(f"Wrote profiles_{tag}.parquet, missingness_by_station_{tag}.csv, missingness_by_year_{tag}.csv to {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build station traffic-pattern profiles")
    parser.add_argument("--month", type=int, default=4)
    parser.add_argument("--tag", type=str, default="apr")
    args = parser.parse_args()
    main(target_month=args.month, tag=args.tag)
