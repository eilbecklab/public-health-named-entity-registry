"""Assemble, prepare, checksum, and verify deterministic registry bundles."""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from .config import project_root
from .export_csv import export_csv
from .export_neo4j import export_neo4j
from .loader import load_registry
from .review_report import build_review
from .schema_generation import generate_schema_artifacts
from .schema_validation import SchemaValidator
from .validation import has_errors, validate_records
from .yaml_io import dump_json, dump_yaml, load_yaml


class ReleaseError(RuntimeError):
    pass


def _timestamp(root: Path) -> dt.datetime:
    source_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_epoch:
        return dt.datetime.fromtimestamp(int(source_epoch), tz=dt.UTC).replace(microsecond=0)
    commit_timestamp = _git(root, "show", "-s", "--format=%cI", "HEAD")
    if commit_timestamp:
        return dt.datetime.fromisoformat(commit_timestamp.replace("Z", "+00:00")).replace(
            microsecond=0
        )
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _git(root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_state(root: Path) -> tuple[str, bool, bool]:
    inside = _git(root, "rev-parse", "--is-inside-work-tree") == "true"
    if not inside:
        return "unversioned", False, False
    commit = _git(root, "rev-parse", "HEAD") or "uncommitted"
    dirty = bool(_git(root, "status", "--porcelain"))
    return commit, dirty, True


def _schema_version(root: Path) -> str:
    schema = load_yaml(
        root
        / "src"
        / "public_health_named_entity_registry"
        / "schema"
        / "public_health_named_entity_registry.yaml"
    )
    return str(schema.get("version", "unknown")) if isinstance(schema, dict) else "unknown"


def _release_id(root: Path, year: int) -> str:
    pattern = re.compile(rf"^phner-release-{year}-([0-9]{{3}})$")
    maximum = 0
    manifests = [
        root / "build" / "release-manifest.yaml",
        *sorted((root / "releases").glob("*/release-manifest.yaml")),
    ]
    for path in manifests:
        if not path.exists():
            continue
        data = load_yaml(path)
        value = data.get("release_id") if isinstance(data, dict) else None
        match = pattern.fullmatch(value) if isinstance(value, str) else None
        if match:
            maximum = max(maximum, int(match.group(1)))
    return f"phner-release-{year}-{maximum + 1:03d}"


def _write_checksums(destination: Path) -> Path:
    checksum_path = destination / "checksums.txt"
    lines: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path == checksum_path:
            continue
        relative = path.relative_to(destination).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {relative}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def build_bundle(
    root: Path | None = None,
    destination: Path | None = None,
    *,
    version: str = "0.0.0",
    status: str = "development",
    release_id: str | None = None,
    release_policy: bool = False,
    include_schema_artifacts: bool = True,
) -> Path:
    root = project_root(root)
    requested_destination = destination or root / "build"
    if requested_destination.is_symlink():
        raise ReleaseError(f"Refusing symlink build destination: {requested_destination}")
    destination = requested_destination.resolve()
    if destination in {Path("/"), Path.home().resolve(), root} or len(destination.parts) < 3:
        raise ReleaseError(f"Refusing unsafe build destination: {destination}")
    marker = destination / ".phner-build"
    default_build = destination == (root / "build").resolve()
    if (
        destination.exists()
        and not default_build
        and any(destination.iterdir())
        and not marker.is_file()
    ):
        raise ReleaseError(
            f"Refusing to replace unmarked non-empty build destination: {destination}"
        )
    registry = load_registry(root)
    issues = validate_records(registry, root, release=release_policy)
    if has_errors(issues):
        details = "\n".join(
            f"{issue.path}: [{issue.code}] {issue.message}"
            for issue in issues
            if issue.severity == "error"
        )
        raise ReleaseError(f"Registry validation failed:\n{details}")
    generated_at = _timestamp(root)
    commit, _dirty, _inside = git_state(root)
    schema_version = _schema_version(root)
    manifest = {
        "release_id": release_id or f"phner-release-{generated_at.year}-000",
        "version": version,
        "released_at": generated_at.isoformat().replace("+00:00", "Z"),
        "schema_version": schema_version,
        "git_commit": commit,
        "status": status,
        "notes": None,
    }
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    marker.write_text("Generated by PHNER; safe for PHNER to replace.\n", encoding="utf-8")
    assembled = registry.as_registry(manifest)
    dump_yaml(assembled, destination / "registry.yaml")
    dump_json(assembled, destination / "registry.json")
    dump_yaml(manifest, destination / "release-manifest.yaml")
    export_csv(registry, destination)
    export_neo4j(registry, destination / "neo4j", root, version, schema_version)
    quality, review = build_review(registry, issues, generated_at.date())
    dump_json(quality, destination / "quality-report.json")
    (destination / "review-report.md").write_text(review, encoding="utf-8")
    release_notes = (
        f"# PHNER {version}\n\n"
        f"- Release ID: {manifest['release_id']}\n"
        f"- Schema version: {schema_version}\n"
        f"- Git commit: {commit}\n"
        f"- Entities: {len(registry.records_of_type('entity'))}\n"
        f"- Relationships: {len(registry.records_of_type('relationship'))}\n"
        f"- Participations: {len(registry.records_of_type('participation'))}\n"
        f"- Evidence sources: {len(registry.records_of_type('source'))}\n"
    )
    (destination / "RELEASE_NOTES.md").write_text(release_notes, encoding="utf-8")
    if include_schema_artifacts:
        generate_schema_artifacts(root, destination / "schema")
    _write_checksums(destination)
    return destination


def prepare_release(
    version: str,
    root: Path | None = None,
    destination: Path | None = None,
    allow_dirty: bool = False,
) -> Path:
    root = project_root(root)
    commit, dirty, inside = git_state(root)
    if not inside and not allow_dirty:
        raise ReleaseError("Release preparation requires Git; use --allow-dirty to acknowledge.")
    if dirty and not allow_dirty:
        raise ReleaseError("Working tree is dirty; commit changes or pass --allow-dirty.")
    now = _timestamp(root)
    release_id = _release_id(root, now.year)
    return build_bundle(
        root,
        destination,
        version=version,
        status="candidate",
        release_id=release_id,
        release_policy=True,
    )


def verify_release(destination: Path, root: Path | None = None) -> None:
    root = project_root(root)
    checksum_path = destination / "checksums.txt"
    if not checksum_path.exists():
        raise ReleaseError(f"Missing {checksum_path}")
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, separator, relative = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ReleaseError(f"Malformed checksum line: {line}")
        path = (destination / relative).resolve()
        try:
            path.relative_to(destination.resolve())
        except ValueError as error:
            raise ReleaseError(f"Unsafe checksum path: {relative}") from error
        if not path.is_file():
            raise ReleaseError(f"Missing release file: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ReleaseError(f"Checksum mismatch: {relative}")
    expected_files = {
        line.partition("  ")[2] for line in checksum_path.read_text(encoding="utf-8").splitlines()
    }
    actual_files = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and path != checksum_path
    }
    unexpected = sorted(actual_files - expected_files)
    if unexpected:
        raise ReleaseError(f"Unlisted release file: {unexpected[0]}")
    assembled = load_yaml(destination / "registry.yaml")
    if not isinstance(assembled, dict):
        raise ReleaseError("registry.yaml is not a mapping")
    release_data = assembled.get("release")
    release_issues = SchemaValidator(root).validate_object(
        release_data,
        "RegistryRelease",
        str(destination / "registry.yaml"),
        str(release_data.get("release_id", "")) if isinstance(release_data, dict) else "",
        "Registry.release",
    )
    if has_errors(release_issues):
        raise ReleaseError(
            "Release metadata validation failed: "
            + "; ".join(issue.message for issue in release_issues)
        )
    from .models import Record, RegistryData

    records: list[Record] = []
    mapping = {
        "entities": ("entity", "NamedEntity", "entity_id"),
        "relationships": ("relationship", "EntityRelationship", "relationship_id"),
        "participations": ("participation", "PlatformParticipation", "participation_id"),
        "evidence": ("source", "EvidenceSource", "source_id"),
    }
    for collection, (record_type, class_name, id_field) in mapping.items():
        values = assembled.get(collection, [])
        if not isinstance(values, list):
            raise ReleaseError(f"registry.yaml {collection} must be a list")
        for data in values:
            if not isinstance(data, dict):
                raise ReleaseError(f"registry.yaml {collection} contains a non-mapping")
            records.append(
                Record(
                    record_type,
                    class_name,
                    str(data.get(id_field, "")),
                    data,
                    destination / "registry.yaml",
                )
            )
    issues = validate_records(RegistryData(records), root, release=True)
    if has_errors(issues):
        raise ReleaseError(
            "Assembled registry validation failed: "
            + "; ".join(issue.message for issue in issues if issue.severity == "error")
        )
