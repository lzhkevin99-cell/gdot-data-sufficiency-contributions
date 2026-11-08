"""Station traffic-pattern profiles (day-of-week reduction).

Profiles are a fixed-length 7-element day-of-week mean vector, not a full daily
vector. This is a deliberate MVP simplification: a 7-length DOW reduction is the
same length for every station regardless of month length or starting weekday, so
clustering never needs `preprocess.realignment_permutation`/`realign` (the
machinery `reference_pool.py` uses to compare two stations' full daily vectors).
Upgrading to full-length, realigned profiles is a labeled Phase 2 extension.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modules import preprocess as pp

# New parameter, no existing precedent in the codebase. Set to 0.90 to mirror the
# two existing 0.90 thresholds already used elsewhere in the pipeline (R_MIN,
# SUFFICIENCY_THRESHOLD in run_multi_site.py) purely for consistency of "what
# counts as good enough" language across the project -- a judgment call, not a
# derived value.
PROFILE_COMPLETENESS_MIN = 0.90

DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def dow_profile(daily_volumes, starting_weekday: int) -> np.ndarray:
    """7-length mean-by-day-of-week vector (Mon..Sun) for one station-month."""
    v = np.asarray(daily_volumes, dtype=float)
    dow = pp.day_of_week(starting_weekday, len(v))
    return np.array(
        [v[dow == d].mean() if (dow == d).any() else np.nan for d in range(7)]
    )


def build_station_profiles(
    cm_all: pd.DataFrame,
    target_month: int,
    exclude_year: int | None = None,
    completeness: pd.DataFrame | None = None,
    completeness_min: float = PROFILE_COMPLETENESS_MIN,
) -> pd.DataFrame:
    """One row per site: raw + shape-normalized 7-vector for `target_month`.

    Averages `dow_profile` across every available year of `target_month` present
    in `cm_all` (the `complete_months_all` schema, which by construction holds
    only complete, quality-clean months -- so profile *values* are never built
    from a partial/incomplete month).

    `completeness` (from `missingness.missingness_report()["by_station"]`, built
    off the full daily inventory, not `cm_all`) gates whether a station has
    *enough history overall* to trust its profile -- a station can have a few
    clean complete months in `cm_all` while still being mostly missing across its
    full history, which `cm_all` alone can't reveal. If `completeness` is not
    supplied, every station with >=1 complete month is marked `included=True`
    and it's the caller's responsibility to gate separately.

    `exclude_year`: drop this year before averaging. Required whenever a specific
    target station-month is about to be evaluated by `fallback.run_station_month`,
    so the cluster label used to pick fallback siblings is never informed by the
    exact year/month whose data-sufficiency is being simulated (leakage guard,
    one level up from `reference_pool.build_candidate_set`'s target-exclusion).
    """
    sub = cm_all[cm_all["month"] == target_month].copy()
    if exclude_year is not None:
        sub = sub[sub["year"] != exclude_year]

    rows = []
    for site, g in sub.groupby("site"):
        stacked = np.vstack(
            [dow_profile(r["daily_volumes"], r["starting_weekday"]) for _, r in g.iterrows()]
        )
        raw = np.nanmean(stacked, axis=0)
        if np.any(np.isnan(raw)):
            continue  # some DOW never observed for this site/month across all years
        shape = raw / raw.mean()
        rows.append(
            dict(
                site=site,
                n_years_used=len(g),
                **{f"raw_{d}": raw[i] for i, d in enumerate(DOW_LABELS)},
                **{f"shape_{d}": shape[i] for i, d in enumerate(DOW_LABELS)},
            )
        )
    profiles_df = pd.DataFrame(rows)
    if profiles_df.empty:
        return profiles_df

    if completeness is not None and not completeness.empty:
        comp = completeness[["site", "mean_completeness"]].rename(
            columns={"mean_completeness": "profile_completeness"}
        )
        profiles_df = profiles_df.merge(comp, on="site", how="left")
        profiles_df["profile_completeness"] = profiles_df["profile_completeness"].fillna(0.0)
        profiles_df["included"] = profiles_df["profile_completeness"] >= completeness_min
    else:
        profiles_df["profile_completeness"] = np.nan
        profiles_df["included"] = True

    return profiles_df


def raw_matrix(profiles_df: pd.DataFrame) -> np.ndarray:
    return profiles_df[[f"raw_{d}" for d in DOW_LABELS]].to_numpy(dtype=float)


def shape_matrix(profiles_df: pd.DataFrame) -> np.ndarray:
    return profiles_df[[f"shape_{d}" for d in DOW_LABELS]].to_numpy(dtype=float)
