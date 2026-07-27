"""Unified validation entry points and custom record rules."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .config import project_root
from .graph_validation import validate_registry_graph
from .loader import load_record, load_registry
from .models import Issue, Record, RegistryData
from .schema_validation import SchemaValidator
from .temporal_validation import validate_temporal

HASH_PATTERN = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


def _issue(record: Record, code: str, message: str, severity: str = "error") -> Issue:
    return Issue(severity, code, message, str(record.path), record.identifier)  # type: ignore[arg-type]


def validate_custom_record(record: Record, release: bool = False) -> list[Issue]:
    issues = validate_temporal(record)
    data = record.data
    if record.record_type == "entity":
        name = data.get("preferred_name")
        if isinstance(name, str) and not name.strip():
            issues.append(_issue(record, "blank-name", "preferred_name cannot be blank."))
        aliases: list[str] = []
        for index, alias in enumerate(data.get("names", [])):
            if not isinstance(alias, dict):
                continue
            value = alias.get("value")
            if isinstance(value, str):
                if not value.strip():
                    issues.append(
                        _issue(record, "blank-alias", f"names[{index}].value cannot be blank.")
                    )
                normalized = " ".join(value.casefold().split())
                if normalized in aliases:
                    issues.append(
                        _issue(record, "duplicate-alias", f"Duplicate alias at names[{index}].")
                    )
                aliases.append(normalized)
        for index, location in enumerate(data.get("locations", [])):
            if not isinstance(location, dict):
                continue
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            if isinstance(latitude, (int, float)) and not -90 <= latitude <= 90:
                issues.append(
                    _issue(
                        record,
                        "invalid-latitude",
                        f"locations[{index}].latitude is out of range.",
                    )
                )
            if isinstance(longitude, (int, float)) and not -180 <= longitude <= 180:
                issues.append(
                    _issue(
                        record,
                        "invalid-longitude",
                        f"locations[{index}].longitude is out of range.",
                    )
                )
        curation = data.get("curation", {})
        notes = curation.get("notes") if isinstance(curation, dict) else None
        if (
            data.get("entity_type") == "other" or "other" in data.get("classifications", [])
        ) and not (isinstance(notes, str) and notes.strip()):
            issues.append(
                _issue(record, "unexplained-other", "Use of 'other' requires curation.notes.")
            )
        if data.get("status") == "active" and not data.get("official_urls"):
            issues.append(
                _issue(
                    record,
                    "active-without-official-url",
                    "Active entity has no official URL.",
                    "warning",
                )
            )
        if any(
            isinstance(location, dict) and location.get("location_type") == "other"
            for location in data.get("locations", [])
        ) and not (isinstance(notes, str) and notes.strip()):
            issues.append(
                _issue(
                    record,
                    "unexplained-other",
                    "Location type 'other' requires curation.notes.",
                )
            )
    if record.record_type == "source":
        content_hash = data.get("content_hash")
        if content_hash and (
            not isinstance(content_hash, str) or HASH_PATTERN.fullmatch(content_hash) is None
        ):
            issues.append(
                _issue(
                    record,
                    "invalid-content-hash",
                    "content_hash must be 64 hex characters, optionally prefixed sha256:.",
                )
            )
        if not data.get("url") and not data.get("document_identifier"):
            issues.append(
                _issue(
                    record,
                    "source-without-locator",
                    "Evidence should include url or document_identifier.",
                    "warning",
                )
            )
    if record.record_type in {"entity", "relationship", "participation"}:
        source_ids = data.get("source_ids", [])
        if not source_ids:
            severity = "error" if release else "warning"
            issues.append(
                _issue(record, "missing-evidence", "Record has no supporting evidence.", severity)
            )
        curation = data.get("curation", {})
        if isinstance(curation, dict):
            status = curation.get("assertion_status")
            notes = curation.get("notes")
            if status == "verified":
                if not curation.get("last_reviewed"):
                    issues.append(
                        _issue(
                            record,
                            "verified-without-review-date",
                            "Verified assertions require curation.last_reviewed.",
                        )
                    )
                reviewed_by = curation.get("reviewed_by")
                if not isinstance(reviewed_by, str) or not reviewed_by.strip():
                    issues.append(
                        _issue(
                            record,
                            "verified-without-reviewer",
                            "Verified assertions require curation.reviewed_by.",
                        )
                    )
            if status == "disputed" and not (isinstance(notes, str) and notes.strip()):
                issues.append(
                    _issue(
                        record,
                        "disputed-without-notes",
                        "Disputed assertions require curation.notes.",
                    )
                )
            if (
                record.record_type == "participation"
                and (
                    "other" in data.get("roles", [])
                    or "other" in data.get("environments", [])
                    or "other" in data.get("data_exchange_modes", [])
                )
                and not (isinstance(notes, str) and notes.strip())
            ):
                issues.append(
                    _issue(
                        record,
                        "unexplained-other",
                        "Participation use of 'other' requires curation.notes.",
                    )
                )
            if release and status in {"candidate", "illustrative"}:
                issues.append(
                    _issue(
                        record,
                        "release-prohibited-status",
                        f"Release cannot contain assertion status {status}.",
                    )
                )
            reviewed = curation.get("last_reviewed")
            if reviewed:
                try:
                    value = (
                        reviewed
                        if isinstance(reviewed, dt.date)
                        else dt.date.fromisoformat(str(reviewed))
                    )
                    if (dt.date.today() - value).days > 365:
                        issues.append(
                            _issue(
                                record,
                                "stale-review",
                                "Record has not been reviewed within 365 days.",
                                "warning",
                            )
                        )
                except ValueError:
                    pass
    return issues


def validate_records(
    registry: RegistryData, root: Path | None = None, release: bool = False
) -> list[Issue]:
    resolved_root = project_root(root)
    issues = list(registry.issues)
    identifiers: dict[str, Record] = {}
    for record in registry.records:
        if record.identifier in identifiers:
            issues.append(
                Issue(
                    "error",
                    "duplicate-identifier",
                    f"Identifier also appears in {identifiers[record.identifier].path}.",
                    str(record.path),
                    record.identifier,
                )
            )
        elif record.identifier:
            identifiers[record.identifier] = record
    schema_validator = SchemaValidator(resolved_root)
    for record in registry.records:
        issues.extend(schema_validator.validate_record(record))
        issues.extend(validate_custom_record(record, release=release))
    issues.extend(validate_registry_graph(registry, resolved_root))
    return sorted(set(issues))


def validate_registry(
    root: Path | None = None, release: bool = False
) -> tuple[RegistryData, list[Issue]]:
    resolved_root = project_root(root)
    registry = load_registry(resolved_root)
    return registry, validate_records(registry, resolved_root, release)


def validate_file(path: Path, root: Path | None = None) -> list[Issue]:
    resolved_root = project_root(root)
    record, issues = load_record(path)
    if record is None:
        return issues
    validator = SchemaValidator(resolved_root)
    return sorted([*issues, *validator.validate_record(record), *validate_custom_record(record)])


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def issue_summary(issues: list[Issue]) -> dict[str, int]:
    return {
        "errors": sum(issue.severity == "error" for issue in issues),
        "warnings": sum(issue.severity == "warning" for issue in issues),
    }
