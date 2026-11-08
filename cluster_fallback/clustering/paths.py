"""Locate the GDoT project checkout this code runs against.

The cluster-fallback MVP reuses the main paper's pipeline (`code/modules/`,
`code/run_multi_site.py`) and its shipped data (`code/data/`, `code/cache/`)
read-only. That pipeline is not part of this repository, so point
`GDOT_PROJECT_ROOT` at the project checkout -- the directory that contains
`code/`:

    export GDOT_PROJECT_ROOT=/path/to/gdot-project
"""
from __future__ import annotations

import os

_ENV_VAR = "GDOT_PROJECT_ROOT"


def _resolve_project_root() -> str:
    root = os.environ.get(_ENV_VAR)
    if not root:
        raise RuntimeError(
            f"{_ENV_VAR} is not set. Set it to the GDoT project checkout "
            "(the directory containing code/modules, code/data and code/cache)."
        )
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(os.path.join(root, "code", "modules")):
        raise RuntimeError(
            f"{_ENV_VAR}={root} does not contain code/modules/. It must point "
            "at the GDoT project checkout, not at this repository."
        )
    return root


PROJECT_ROOT = _resolve_project_root()
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
DATA_DIR = os.path.join(CODE_DIR, "data")
CACHE_DIR = os.path.join(CODE_DIR, "cache")
