"""Load canonical one-record-per-file YAML without touching candidates or fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import DIRECTORY_TO_TYPE, RECORD_CONFIG, project_root
from .models import Issue, Record, RegistryData
from .yaml_io import load_yaml


def infer_record_type(path: Path) -> str | None:
    for parent in path.parents:
        if parent.name in DIRECTORY_TO_TYPE:
            return DIRECTORY_TO_TYPE[parent.name]
    return None


def load_record(path: Path, record_type: str | None = None) -> tuple[Record | None, list[Issue]]:
    issues: list[Issue] = []
    selected_type = record_type or infer_record_type(path)
    if selected_type not in RECORD_CONFIG:
        return None, [
            Issue("error", "unknown-record-type", "Cannot infer record type from path.", str(path))
        ]
    config = RECORD_CONFIG[selected_type]
    try:
        raw = load_yaml(path)
    except (OSError, yaml.YAMLError) as error:
        return None, [Issue("error", "invalid-yaml", str(error), str(path))]
    if not isinstance(raw, dict):
        return None, [
            Issue("error", "record-not-mapping", "Top-level YAML must be a mapping.", str(path))
        ]
    id_field = str(config["id_field"])
    identifier_value: Any = raw.get(id_field)
    identifier = identifier_value if isinstance(identifier_value, str) else ""
    if not identifier:
        issues.append(
            Issue("error", "missing-identifier", f"Missing string field {id_field}.", str(path))
        )
    return (
        Record(selected_type, str(config["class"]), identifier, raw, path),
        issues,
    )


def load_registry(root: Path | None = None) -> RegistryData:
    root = project_root(root)
    result = RegistryData()
    seen: dict[str, Path] = {}
    for record_type, config in RECORD_CONFIG.items():
        directory = root / "data" / str(config["directory"])
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.yaml")):
            record, issues = load_record(path, record_type)
            result.issues.extend(issues)
            if record is None:
                continue
            if record.identifier and record.identifier in seen:
                result.issues.append(
                    Issue(
                        "error",
                        "duplicate-identifier",
                        f"Identifier also appears in {seen[record.identifier]}.",
                        str(path),
                        record.identifier,
                    )
                )
            else:
                seen[record.identifier] = path
            result.records.append(record)
    return result
