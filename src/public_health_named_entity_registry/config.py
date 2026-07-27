"""Project paths and record-type configuration."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT_ROOT = PACKAGE_ROOT.parents[1]

RECORD_CONFIG = {
    "entity": {
        "directory": "entities",
        "class": "NamedEntity",
        "id_field": "entity_id",
        "prefix": "phner-ent-",
        "template": "entity.yaml",
        "collection": "entities",
    },
    "relationship": {
        "directory": "relationships",
        "class": "EntityRelationship",
        "id_field": "relationship_id",
        "prefix": "phner-rel-",
        "template": "relationship.yaml",
        "collection": "relationships",
    },
    "participation": {
        "directory": "participations",
        "class": "PlatformParticipation",
        "id_field": "participation_id",
        "prefix": "phner-par-",
        "template": "participation.yaml",
        "collection": "participations",
    },
    "source": {
        "directory": "evidence",
        "class": "EvidenceSource",
        "id_field": "source_id",
        "prefix": "phner-src-",
        "template": "evidence.yaml",
        "collection": "evidence",
    },
}

DIRECTORY_TO_TYPE = {value["directory"]: key for key, value in RECORD_CONFIG.items()}


def project_root(explicit: Path | None = None) -> Path:
    """Resolve the project root, allowing tests and callers to override it."""
    if explicit is not None:
        return explicit.resolve()
    configured = os.environ.get("PHNER_PROJECT_ROOT")
    return Path(configured).resolve() if configured else DEFAULT_PROJECT_ROOT


def schema_path(root: Path) -> Path:
    return (
        root
        / "src"
        / "public_health_named_entity_registry"
        / "schema"
        / "public_health_named_entity_registry.yaml"
    )
