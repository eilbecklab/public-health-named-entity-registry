"""Whole-registry referential and graph-policy validation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Issue, Record, RegistryData
from .temporal_validation import is_current
from .yaml_io import load_yaml


def _record_issue(record: Record, code: str, message: str, severity: str = "error") -> Issue:
    return Issue(severity, code, message, str(record.path), record.identifier)  # type: ignore[arg-type]


def _source_references(data: Any, field_path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            next_path = f"{field_path}.{key}" if field_path else key
            if key == "source_ids" and isinstance(value, list):
                found.extend(
                    (source_id, next_path) for source_id in value if isinstance(source_id, str)
                )
            else:
                found.extend(_source_references(value, next_path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_source_references(value, f"{field_path}[{index}]"))
    return found


def validate_registry_graph(registry: RegistryData, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    entities = {item.identifier: item for item in registry.records_of_type("entity")}
    sources = {item.identifier for item in registry.records_of_type("source")}
    rules_raw = load_yaml(root / "mappings" / "relationship_rules.yaml")
    rules: dict[str, dict[str, Any]] = rules_raw if isinstance(rules_raw, dict) else {}

    for record in registry.records:
        for source_id, field_path in _source_references(record.data):
            if source_id not in sources:
                issues.append(
                    _record_issue(
                        record,
                        "missing-source-reference",
                        f"{field_path} references unknown evidence {source_id}.",
                    )
                )

    edges_by_type: dict[str, list[Record]] = defaultdict(list)
    active_edge_keys: dict[tuple[str, str, str], Record] = {}
    current_objects: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for record in registry.records_of_type("relationship"):
        subject_id = record.data.get("subject_entity_id")
        object_id = record.data.get("object_entity_id")
        relationship_type = record.data.get("relationship_type")
        if subject_id not in entities:
            issues.append(
                _record_issue(record, "missing-subject", f"Unknown subject entity {subject_id}.")
            )
        if object_id not in entities:
            issues.append(
                _record_issue(record, "missing-object", f"Unknown object entity {object_id}.")
            )
        if subject_id == object_id and subject_id:
            issues.append(
                _record_issue(record, "self-relationship", "Self-relationships are prohibited.")
            )
        if not isinstance(relationship_type, str):
            continue
        edges_by_type[relationship_type].append(record)
        rule = rules.get(relationship_type, {})
        if subject_id in entities:
            allowed = rule.get("subject_types")
            actual = entities[subject_id].data.get("entity_type")
            if isinstance(allowed, list) and actual not in allowed:
                issues.append(
                    _record_issue(
                        record,
                        "invalid-subject-type",
                        f"{relationship_type} does not allow subject type {actual}.",
                    )
                )
        if object_id in entities:
            allowed = rule.get("object_types")
            actual = entities[object_id].data.get("entity_type")
            if isinstance(allowed, list) and actual not in allowed:
                issues.append(
                    _record_issue(
                        record,
                        "invalid-object-type",
                        f"{relationship_type} does not allow object type {actual}.",
                    )
                )
            if is_current(record.data) and entities[object_id].data.get("status") in {
                "inactive",
                "superseded",
                "dissolved",
            }:
                issues.append(
                    _record_issue(
                        record,
                        "inactive-current-target",
                        f"Current relationship targets {object_id}, which is not active.",
                        "warning",
                    )
                )
        if rule.get("requires_identity_review") and not record.data.get("identity_review"):
            issues.append(
                _record_issue(
                    record,
                    "missing-identity-review",
                    f"{relationship_type} requires identity_review metadata.",
                )
            )
        if is_current(record.data) and isinstance(subject_id, str) and isinstance(object_id, str):
            key = (subject_id, relationship_type, object_id)
            if key in active_edge_keys:
                issues.append(
                    _record_issue(
                        record,
                        "duplicate-active-edge",
                        f"Duplicates current edge in {active_edge_keys[key].path}.",
                    )
                )
            active_edge_keys[key] = record
            current_objects[(subject_id, relationship_type)].append(record)

    for (subject_id, relationship_type, object_id), record in sorted(active_edge_keys.items()):
        rule = rules.get(relationship_type, {})
        inverse = rule.get("inverse")
        if (
            isinstance(inverse, str)
            and (
                subject_id,
                inverse,
                object_id,
            )
            in active_edge_keys
        ):
            other = active_edge_keys[(subject_id, inverse, object_id)]
            if record.identifier < other.identifier:
                issues.append(
                    _record_issue(
                        record,
                        "inverse-direction-contradiction",
                        f"{relationship_type} and {inverse} use the same direction for "
                        f"{subject_id} and {object_id}.",
                    )
                )
        reverse_key = (object_id, relationship_type, subject_id)
        if (
            rule.get("symmetric")
            and reverse_key in active_edge_keys
            and record.identifier < active_edge_keys[reverse_key].identifier
        ):
            issues.append(
                _record_issue(
                    record,
                    "duplicate-symmetric-edge",
                    f"{relationship_type} is asserted in both directions for "
                    f"{subject_id} and {object_id}.",
                )
            )

    for relationship_type, rule in rules.items():
        maximum = rule.get("max_current_objects")
        if not isinstance(maximum, int):
            continue
        for (subject_id, edge_type), records in current_objects.items():
            if edge_type == relationship_type and len(records) > maximum:
                issues.append(
                    _record_issue(
                        records[-1],
                        "too-many-current-relationships",
                        f"{subject_id} has {len(records)} current {edge_type} "
                        f"objects; max is {maximum}.",
                    )
                )

    for relationship_type, edge_records in edges_by_type.items():
        if rules.get(relationship_type, {}).get("acyclic"):
            issues.extend(_cycle_issues(relationship_type, edge_records))

    for record in registry.records_of_type("participation"):
        entity_id = record.data.get("entity_id")
        platform_id = record.data.get("platform_entity_id")
        if entity_id not in entities:
            issues.append(
                _record_issue(record, "missing-participant", f"Unknown entity {entity_id}.")
            )
        if platform_id not in entities:
            issues.append(
                _record_issue(record, "missing-platform", f"Unknown platform {platform_id}.")
            )
        elif entities[platform_id].data.get("entity_type") != "platform":
            issues.append(
                _record_issue(
                    record,
                    "invalid-platform-type",
                    f"{platform_id} must have entity_type platform.",
                )
            )

    for record in registry.records_of_type("entity"):
        for index, location in enumerate(record.data.get("locations", [])):
            if not isinstance(location, dict):
                continue
            jurisdiction_id = location.get("jurisdiction_entity_id")
            if jurisdiction_id is None:
                continue
            if jurisdiction_id not in entities:
                issues.append(
                    _record_issue(
                        record,
                        "missing-location-jurisdiction",
                        f"locations[{index}] references unknown entity {jurisdiction_id}.",
                    )
                )
            elif entities[jurisdiction_id].data.get("entity_type") != "jurisdiction":
                issues.append(
                    _record_issue(
                        record,
                        "invalid-location-jurisdiction",
                        f"locations[{index}] target {jurisdiction_id} is not a jurisdiction.",
                    )
                )
    return issues


def _cycle_issues(relationship_type: str, records: list[Record]) -> list[Issue]:
    adjacency: dict[str, list[tuple[str, Record]]] = defaultdict(list)
    for record in records:
        if not is_current(record.data):
            continue
        subject = record.data.get("subject_entity_id")
        object_id = record.data.get("object_entity_id")
        if isinstance(subject, str) and isinstance(object_id, str):
            adjacency[subject].append((object_id, record))
    visiting: set[str] = set()
    visited: set[str] = set()
    issues: list[Issue] = []

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            cycle = trail[trail.index(node) :]
            record = adjacency[trail[-1]][0][1]
            issues.append(
                _record_issue(
                    record,
                    "relationship-cycle",
                    f"{relationship_type} cycle: {' -> '.join(cycle)}.",
                )
            )
            return
        if node in visited:
            return
        visiting.add(node)
        for target, _record in adjacency.get(node, []):
            visit(target, [*trail, target])
        visiting.remove(node)
        visited.add(node)

    for start in sorted(adjacency):
        if start not in visited:
            visit(start, [start])
    unique = {(issue.code, issue.message): issue for issue in issues}
    return list(unique.values())
