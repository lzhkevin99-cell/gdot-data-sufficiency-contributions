"""KMeans clustering of station profiles, with K-selection diagnostics.

No clustering utilities exist anywhere else in this codebase -- this is entirely
new functionality, built only on scikit-learn primitives already installed
(confirmed 1.5.1) via the existing `scikit-learn>=1.3` pin in requirements.txt.
No new dependency is needed for KMeans/silhouette/Calinski-Harabasz/Davies-Bouldin.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

# Reused, not redefined: this is the exact seed run_multi_site.py hardcodes at
# line 243 and the root README documents as the project-wide reproducibility seed.
CLUSTER_SEED = 42
CLUSTER_K_RANGE = range(2, 13)


def fit_kmeans_sweep(
    X: np.ndarray, k_range=CLUSTER_K_RANGE, seed: int = CLUSTER_SEED
) -> pd.DataFrame:
    """Fit KMeans for each K in `k_range` on standardized `X`.

    Returns one row per K with inertia (elbow), silhouette, Calinski-Harabasz,
    and Davies-Bouldin scores, plus the fitted-model cluster-size distribution.
    """
    Xs = StandardScaler().fit_transform(X)
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = km.fit_predict(Xs)
        sizes = np.bincount(labels)
        rows.append(
            dict(
                k=k,
                inertia=km.inertia_,
                silhouette=silhouette_score(Xs, labels),
                calinski_harabasz=calinski_harabasz_score(Xs, labels),
                davies_bouldin=davies_bouldin_score(Xs, labels),
                min_cluster_size=int(sizes.min()),
                max_cluster_size=int(sizes.max()),
            )
        )
    return pd.DataFrame(rows)


def select_k(sweep_df: pd.DataFrame) -> int:
    """MVP K-selection rule: argmax silhouette score.

    One defensible, simple rule -- not claimed as the only valid one. Phase 2
    can compare this against elbow/Calinski-Harabasz/Davies-Bouldin agreement
    and a parsimony preference when criteria disagree.
    """
    return int(sweep_df.loc[sweep_df["silhouette"].idxmax(), "k"])


def fit_final(
    X: np.ndarray, k: int, seed: int = CLUSTER_SEED
) -> tuple[np.ndarray, np.ndarray, StandardScaler, KMeans]:
    """Fit the final KMeans model at the chosen K.

    Returns (labels, centroids_in_original_units, fitted_scaler, fitted_kmeans).
    `fitted_kmeans` is returned alongside so `centroid_distances` can reuse its
    (standardized-space) `cluster_centers_` directly rather than re-deriving them
    from the inverse-transformed, original-unit centroids returned for plotting.
    """
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = km.fit_predict(Xs)
    centroids = scaler.inverse_transform(km.cluster_centers_)
    return labels, centroids, scaler, km


def centroid_distances(
    X: np.ndarray, labels: np.ndarray, scaler: StandardScaler, km: KMeans
) -> np.ndarray:
    """Euclidean distance (in standardized space) from each row to its own cluster centroid."""
    Xs = scaler.transform(X)
    return np.array([
        np.linalg.norm(Xs[i] - km.cluster_centers_[labels[i]]) for i in range(len(labels))
    ])
