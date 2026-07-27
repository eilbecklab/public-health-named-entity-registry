"""Deterministic curator-facing quality and review reports."""

from __future__ import annotations

import collections
import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

from .duplicate_detection import DuplicateCandidate, find_duplicates
from .models import Issue, Record, RegistryData
from .validation import issue_summary


def _counts(values: list[Any]) -> dict[str, int]:
    counter = collections.Counter(str(value) for value in values if value is not None)
    return dict(sorted(counter.items()))


def quality_report(
    registry: RegistryData, issues: list[Issue], duplicates: list[DuplicateCandidate]
) -> dict[str, Any]:
    entities = registry.records_of_type("entity")
    relationships = registry.records_of_type("relationship")
    participations = registry.records_of_type("participation")
    return {
        "summary": {
            "entities": len(entities),
            "relationships": len(relationships),
            "participations": len(participations),
            "evidence": len(registry.records_of_type("source")),
            **issue_summary(issues),
            "duplicate_candidates": len(duplicates),
        },
        "entities_by_type": _counts([item.data.get("entity_type") for item in entities]),
        "entities_by_status": _counts([item.data.get("status") for item in entities]),
        "entities_by_classification": _counts(
            [
                classification
                for item in entities
                for classification in item.data.get("classifications", [])
            ]
        ),
        "entities_by_jurisdiction_scope": _counts(
            [scope for item in entities for scope in item.data.get("jurisdiction_scopes", [])]
        ),
        "participations_by_role": _counts(
            [role for item in participations for role in item.data.get("roles", [])]
        ),
        "participations_by_status": _counts(
            [item.data.get("lifecycle_status") for item in participations]
        ),
        "issues": [issue.as_dict() for issue in issues],
        "duplicate_candidates": [candidate.as_dict() for candidate in duplicates],
    }


def markdown_report(
    report: dict[str, Any],
    title: str = "PHNER Registry Review",
    generated_on: dt.date | None = None,
) -> str:
    summary = report["summary"]
    lines = [
        f"# {title}",
        "",
        f"Generated: {(generated_on or dt.date.today()).isoformat()}",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
    lines.extend(["", "## Validation findings", ""])
    issues = report.get("issues", [])
    if not issues:
        lines.append("No validation findings.")
    else:
        lines.extend(
            [
                "| Severity | Code | Record | Finding |",
                "|---|---|---|---|",
            ]
        )
        for issue in issues:
            message = str(issue["message"]).replace("|", "\\|")
            lines.append(
                f"| {issue['severity']} | {issue['code']} | "
                f"{issue.get('record_id', '')} | {message} |"
            )
    lines.extend(["", "## Possible duplicates", ""])
    duplicates = report.get("duplicate_candidates", [])
    if not duplicates:
        lines.append("No duplicate candidates met the configured threshold.")
    else:
        lines.extend(["| Entity A | Entity B | Score | Reasons |", "|---|---|---:|---|"])
        for candidate in duplicates:
            reasons = "; ".join(candidate["reasons"]).replace("|", "\\|")
            lines.append(
                f"| {candidate['entity_a']} | {candidate['entity_b']} | "
                f"{candidate['score']:.3f} | {reasons} |"
            )
    return "\n".join(lines) + "\n"


def record_report(record: Record, registry: RegistryData, issues: list[Issue]) -> str:
    related: list[str] = []
    for relationship in registry.records_of_type("relationship"):
        data = relationship.data
        if record.identifier in {data.get("subject_entity_id"), data.get("object_entity_id")}:
            related.append(
                f"- {relationship.identifier}: {data.get('subject_entity_id')} "
                f"{data.get('relationship_type')} {data.get('object_entity_id')}"
            )
    relevant = [issue for issue in issues if issue.record_id == record.identifier]
    lines = [
        f"# Review: {record.identifier}",
        "",
        f"- Type: {record.record_type}",
        f"- Source path: {record.path}",
        f"- Preferred name: {record.data.get('preferred_name', '')}",
        f"- Assertion status: {(record.data.get('curation') or {}).get('assertion_status', '')}",
        f"- Evidence references: {len(record.data.get('source_ids', []))}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(
        [f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in relevant]
        or ["No validation findings for this record."]
    )
    lines.extend(["", "## Relationships", ""])
    lines.extend(sorted(related) or ["No relationships reference this record."])
    return "\n".join(lines) + "\n"


def changed_yaml_files(root: Path, base: str = "origin/main") -> list[Path]:
    check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        raise RuntimeError("changed-file review requires a Git repository")
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    changed_names: set[str] = set()
    if head.returncode == 0:
        merge_base = subprocess.run(
            ["git", "merge-base", base, "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        comparison = merge_base.stdout.strip() if merge_base.returncode == 0 else "HEAD"
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", comparison],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        changed_names.update(result.stdout.splitlines())
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    names = sorted(changed_names | set(untracked.stdout.splitlines()))
    return [
        root / name
        for name in names
        if name.endswith((".yaml", ".yml")) and name.startswith("data/")
    ]


def build_review(
    registry: RegistryData,
    issues: list[Issue],
    generated_on: dt.date | None = None,
) -> tuple[dict[str, Any], str]:
    duplicates = find_duplicates(registry)
    report = quality_report(registry, issues, duplicates)
    return report, markdown_report(report, generated_on=generated_on)
