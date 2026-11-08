"""Cluster-enhanced reference-pool fallback (Step 5 of the MVP).

Wraps the existing, unmodified individual reference-pool pipeline
(`run_multi_site.build_pool_fast`, `modules.reference_pool`, `modules.simulate`)
with an additive fallback: when a station-month's *individual* pool is smaller
than `run_multi_site.MIN_POOL_SIZE`, build an augmented pool from the target's
traffic-pattern cluster instead, then run the exact same downstream simulation.

Per the locked integration decision (see plan), this module reimplements the
~25-line simulation-orchestration tail of `run_multi_site.run_site()`
(day-type/dow computation, `f_true`/`delta`, the `sim.run_simulation` call --
`run_multi_site.py:222-256`) rather than editing `run_multi_site.py`. That
file's "verified reproducible" guarantee (root README status table) is never
touched or reopened for review. `_simulate_tail` below calls the identical
`modules/` primitives `run_site` calls; no new statistical logic is introduced,
only import-level reuse of `run_multi_site`'s constants, `find_companions()`,
and `build_pool_fast()`.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

import run_multi_site as rms
from modules import preprocess as pp
from modules import simulate as sim
from modules.estimators import f_madt

log = logging.getLogger("clustering.fallback")


def _simulate_tail(target_site: str, result: dict, R: int) -> dict:
    """Reimplementation of run_multi_site.run_site()'s post-pool-build tail
    (run_multi_site.py:222-256). Takes an already-built pool `result` (from
    `rms.build_pool_fast`) so callers can supply either the individual or the
    cluster-augmented pool -- `run_site` itself can't be reused directly here
    because it enforces the MIN_POOL_SIZE gate internally and returns None
    below it (run_multi_site.py:217-220), which is exactly the branch this
    module needs to intercept and handle differently.
    """
    target_vec = result["target_vec"]
    pool = result["pool"]
    day_type = pp.day_types_for_month(result["target_start_weekday"], result["n_m"])
    dow = pp.day_of_week(result["target_start_weekday"], result["n_m"])

    ref_vectors = [np.asarray(v, dtype=float) for v in pool["realigned_volumes"]]
    f_values = [f_madt(v) for v in ref_vectors]
    f_true = f_madt(target_vec)
    delta = rms.DELTA_FRAC * f_true

    raw = sim.run_simulation(
        ref_vectors=ref_vectors,
        f_values=f_values,
        target_vec=target_vec,
        day_type=day_type,
        candidate_k=rms.CANDIDATE_K,
        mechanisms=rms.MECHANISMS,
        alpha=rms.ALPHA,
        delta=delta,
        R=R,
        estimator=rms.ESTIMATOR,
        seed=42,
        f_true=f_true,
        dow=dow,
    )
    raw["site"] = target_site
    return {"raw": raw, "f_true": f_true, "delta": delta, "pool_size": result["pool_size"]}


def cluster_siblings(target_site: str, target_cluster_id: int, cluster_labels: pd.DataFrame) -> list[str]:
    """Other sites sharing target_site's cluster label, target excluded."""
    same = cluster_labels.loc[cluster_labels["cluster_id"] == target_cluster_id, "site"]
    return [s for s in same if s != target_site]


def run_station_month(
    target_site: str,
    target_year: int,
    target_month: int,
    meta: pd.DataFrame,
    cm_detrended: pd.DataFrame,
    cluster_labels: pd.DataFrame,
    R: int = rms.R_FULL,
    companions_override: list[str] | None = None,
) -> dict:
    """Individual pool first; cluster-pooled fallback only if the individual
    pool is smaller than `rms.MIN_POOL_SIZE`. Always returns a dict recording
    which of {individual, cluster_fallback, still_insufficient, no_target_data}
    was used -- this is the "record which method was used per station-month"
    requirement; nothing in the existing pipeline persists this today
    (run_multi_site.py:217-220,396-399 silently drops the site instead).

    `sim` in the returned dict is the `_simulate_tail` output (raw replications
    + f_true/delta/pool_size) when a simulation ran, else None.

    `companions_override`: test-only hook for validation.py's holdout design
    (a deterministically truncated companion list, to force a real,
    comfortably-sufficient site into the insufficient branch). Production
    calls should never pass this -- default is the real `rms.find_companions`.
    """
    companions = (
        companions_override if companions_override is not None
        else rms.find_companions(target_site, meta)
    )

    try:
        individual_result = rms.build_pool_fast(
            target_site, target_year, target_month, companions, cm_detrended
        )
    except Exception as e:
        log.warning(f"{target_site}: individual pool build failed — {e}")
        individual_result = None

    base = dict(site=target_site, year=target_year, month=target_month)

    if individual_result is None:
        return dict(
            base, method="no_target_data", cluster_id=None,
            pool_size_individual=0, pool_size_final=0,
            n_cluster_siblings_added=0, sim=None, warning=None,
        )

    pool_size_individual = individual_result["pool_size"]

    if pool_size_individual >= rms.MIN_POOL_SIZE:
        sim_out = _simulate_tail(target_site, individual_result, R)
        return dict(
            base, method="individual", cluster_id=None,
            pool_size_individual=pool_size_individual,
            pool_size_final=pool_size_individual,
            n_cluster_siblings_added=0, sim=sim_out, warning=None,
        )

    # --- Individual pool insufficient: attempt the cluster fallback ---
    cl_row = cluster_labels.loc[cluster_labels["site"] == target_site]
    if cl_row.empty:
        return dict(
            base, method="still_insufficient", cluster_id=None,
            pool_size_individual=pool_size_individual,
            pool_size_final=pool_size_individual,
            n_cluster_siblings_added=0, sim=None,
            warning="no cluster label (target failed the profile-completeness gate)",
        )

    target_cluster_id = int(cl_row.iloc[0]["cluster_id"])
    siblings = cluster_siblings(target_site, target_cluster_id, cluster_labels)
    augmented_companions = sorted(set(companions) | set(siblings))

    try:
        augmented_result = rms.build_pool_fast(
            target_site, target_year, target_month, augmented_companions, cm_detrended
        )
    except Exception as e:
        log.warning(f"{target_site}: cluster-augmented pool build failed — {e}")
        augmented_result = None

    if augmented_result is None or augmented_result["pool_size"] < rms.MIN_POOL_SIZE:
        pool_size_final = augmented_result["pool_size"] if augmented_result else pool_size_individual
        return dict(
            base, method="still_insufficient", cluster_id=target_cluster_id,
            pool_size_individual=pool_size_individual,
            pool_size_final=pool_size_final,
            n_cluster_siblings_added=len(siblings), sim=None, warning=None,
        )

    # Leakage guard: the augmented pool must never contain the target's own
    # row (mirrors reference_pool.build_candidate_set's exclusion of the
    # target, reference_pool.py:46-53, applied one level up to the cluster
    # sibling expansion).
    aug_pool = augmented_result["pool"]
    leak = aug_pool[
        (aug_pool["site"] == target_site)
        & (aug_pool["year"] == target_year)
        & (aug_pool["month"] == target_month)
    ]
    assert leak.empty, f"leakage: target's own row found in augmented pool for {target_site}"

    sim_out = _simulate_tail(target_site, augmented_result, R)
    return dict(
        base, method="cluster_fallback", cluster_id=target_cluster_id,
        pool_size_individual=pool_size_individual,
        pool_size_final=augmented_result["pool_size"],
        n_cluster_siblings_added=len(siblings), sim=sim_out, warning=None,
    )
