"""Project path configuration."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT_ROOT = PACKAGE_ROOT.parents[1]


def project_root(explicit: Path | None = None) -> Path:
    """Resolve the project root, allowing tests and callers to override it."""
    if explicit is not None:
        return explicit.resolve()
    configured = os.environ.get("PHNER_PROJECT_ROOT")
    return Path(configured).resolve() if configured else DEFAULT_PROJECT_ROOT
