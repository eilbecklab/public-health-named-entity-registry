"""Command-line interface for the PHNER Neo4j graph and interchange tooling."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import RECORD_CONFIG, project_root
from .duplicate_detection import find_duplicates
from .identifiers import IdentifierError, reserve_id
from .loader import load_registry
from .models import Issue
from .neo4j_store import (
    Neo4jSettings,
    apply_migrations,
    check_connectivity,
    create_entity,
    create_relationship,
    export_graph,
    graph_stats,
    validate_graph,
)
from .release import ReleaseError, build_bundle, prepare_release, verify_release
from .review_report import build_review, changed_yaml_files, record_report
from .scaffolding import ScaffoldingError, new_record
from .schema_generation import GenerationError, generate_schema_artifacts
from .validation import has_errors, validate_file, validate_registry


def _root(args: argparse.Namespace) -> Path:
    return project_root(Path(args.project_root) if args.project_root else None)


def _print_issues(issues: Sequence[Issue]) -> None:
    if not issues:
        print("Validation passed with no findings.")
        return
    for issue in issues:
        print(f"{issue.path or '-'}: {issue.severity.upper()} [{issue.code}] {issue.message}")
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    print(f"{errors} error(s), {warnings} warning(s)")


def _cmd_new(args: argparse.Namespace) -> int:
    supplied = {
        key: value
        for key, value in {
            "subject_entity_id": args.subject,
            "object_entity_id": args.object,
            "entity_id": args.entity,
            "platform_entity_id": args.platform,
        }.items()
        if value is not None
    }
    path = new_record(
        args.record_type,
        _root(args),
        name_slug=args.name_slug,
        supplied=supplied,
        created_by=args.created_by,
    )
    print(path)
    return 0


def _cmd_reserve(args: argparse.Namespace) -> int:
    print(reserve_id(args.record_type, _root(args)))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    root = _root(args)
    if args.validation_target == "file":
        issues = validate_file(Path(args.path).resolve(), root)
    elif args.validation_target == "changed":
        paths = changed_yaml_files(root, args.base)
        issues = [issue for path in paths for issue in validate_file(path, root)]
    else:
        _registry, issues = validate_registry(root, release=args.release_policy)
    _print_issues(issues)
    return 1 if has_errors(issues) else 0


def _cmd_duplicates(args: argparse.Namespace) -> int:
    candidates = find_duplicates(load_registry(_root(args)), threshold=args.threshold)
    if args.json:
        print(json.dumps([candidate.as_dict() for candidate in candidates], indent=2))
    elif not candidates:
        print("No duplicate candidates met the configured threshold.")
    else:
        for candidate in candidates:
            print(
                f"{candidate.entity_a} <-> {candidate.entity_b}: "
                f"{candidate.score:.3f} ({'; '.join(candidate.reasons)})"
            )
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    root = _root(args)
    registry, issues = validate_registry(root)
    if args.review_target == "record":
        record = registry.by_id.get(args.identifier)
        if record is None:
            raise ValueError(f"Unknown record identifier: {args.identifier}")
        print(record_report(record, registry, issues), end="")
        return 0
    if args.review_target == "changed":
        paths = {path.resolve() for path in changed_yaml_files(root, args.base)}
        selected = [record for record in registry.records if record.path.resolve() in paths]
        if not selected:
            print("No changed canonical YAML records.")
        for record in selected:
            print(record_report(record, registry, issues))
        return 0
    _quality, markdown = build_review(registry, issues)
    print(markdown, end="")
    return 1 if has_errors(issues) else 0


def _cmd_build(args: argparse.Namespace) -> int:
    path = build_bundle(
        _root(args),
        Path(args.output).resolve() if args.output else None,
        include_schema_artifacts=not args.skip_schema_artifacts,
    )
    print(path)
    return 0


def _graph_settings() -> Neo4jSettings:
    return Neo4jSettings.from_env()


def _cmd_graph_check(args: argparse.Namespace) -> int:
    settings = _graph_settings()
    information = check_connectivity(settings, wait_seconds=args.wait_seconds)
    print(
        f"Connected to {information['address']} ({information['agent']}), "
        f"database {information['database']}."
    )
    return 0


def _cmd_graph_init(args: argparse.Namespace) -> int:
    applied, skipped = apply_migrations(_graph_settings(), _root(args))
    for name in applied:
        print(f"Applied {name}")
    for name in skipped:
        print(f"Already applied {name}")
    return 0


def _cmd_graph_new_entity(args: argparse.Namespace) -> int:
    identifier = create_entity(
        _graph_settings(),
        args.name,
        args.entity_type,
        created_by=args.created_by,
        root=_root(args),
    )
    print(identifier)
    return 0


def _cmd_graph_new_relationship(args: argparse.Namespace) -> int:
    identifier = create_relationship(
        _graph_settings(),
        args.subject,
        args.relationship_type,
        args.object,
        created_by=args.created_by,
        root=_root(args),
    )
    print(identifier)
    return 0


def _cmd_graph_validate(args: argparse.Namespace) -> int:
    findings = validate_graph(_graph_settings(), _root(args))
    if not findings:
        print("Graph validation passed with no findings.")
        return 0
    for finding in findings:
        print(
            f"{finding.identifier}: {finding.severity.upper()} "
            f"[{finding.code}] {finding.message}"
        )
    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    print(f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def _cmd_graph_stats(args: argparse.Namespace) -> int:
    counts = graph_stats(_graph_settings())
    if args.json:
        print(json.dumps(counts, indent=2, sort_keys=True))
    else:
        for label, count in counts.items():
            print(f"{label}: {count}")
    return 0


def _cmd_graph_export(args: argparse.Namespace) -> int:
    root = _root(args)
    destination = (
        Path(args.output).resolve()
        if args.output
        else root / "build" / "neo4j-snapshot.json"
    )
    print(export_graph(_graph_settings(), destination))
    return 0


def _cmd_generate_schema(args: argparse.Namespace) -> int:
    root = _root(args)
    output = Path(args.output).resolve() if args.output else root / "build" / "schema"
    generate_schema_artifacts(root, output)
    print(output)
    return 0


def _cmd_release_prepare(args: argparse.Namespace) -> int:
    path = prepare_release(
        args.version,
        _root(args),
        Path(args.output).resolve() if args.output else None,
        allow_dirty=args.allow_dirty,
    )
    print(path)
    return 0


def _cmd_release_verify(args: argparse.Namespace) -> int:
    verify_release(Path(args.path).resolve(), _root(args))
    print(f"Verified release bundle: {Path(args.path).resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phner", description=__doc__)
    parser.add_argument("--project-root", help="Override the PHNER repository root.")
    commands = parser.add_subparsers(dest="command", required=True)

    graph = commands.add_parser(
        "graph",
        help="Manage the canonical Neo4j property graph.",
    )
    graph_commands = graph.add_subparsers(dest="graph_command", required=True)
    graph_check = graph_commands.add_parser("check", help="Verify Neo4j connectivity.")
    graph_check.add_argument(
        "--wait-seconds",
        type=int,
        default=0,
        help="Wait up to this many seconds for Neo4j to become available.",
    )
    graph_check.set_defaults(function=_cmd_graph_check)

    graph_init = graph_commands.add_parser(
        "init",
        help="Apply repository-controlled graph migrations.",
    )
    graph_init.set_defaults(function=_cmd_graph_init)

    graph_new_entity = graph_commands.add_parser(
        "new-entity",
        help="Create a minimally valid NamedEntity node.",
    )
    graph_new_entity.add_argument("--name", required=True, help="Preferred display name.")
    graph_new_entity.add_argument(
        "--type",
        dest="entity_type",
        required=True,
        help="Entity type defined by mappings/neo4j_mapping.yaml.",
    )
    graph_new_entity.add_argument("--created-by", help="Editor identity to record.")
    graph_new_entity.set_defaults(function=_cmd_graph_new_entity)

    graph_new_relationship = graph_commands.add_parser(
        "new-relationship",
        help="Create an identified relationship between NamedEntity nodes.",
    )
    graph_new_relationship.add_argument("--subject", required=True)
    graph_new_relationship.add_argument("--type", dest="relationship_type", required=True)
    graph_new_relationship.add_argument("--object", required=True)
    graph_new_relationship.add_argument("--created-by", help="Editor identity to record.")
    graph_new_relationship.set_defaults(function=_cmd_graph_new_relationship)

    graph_validate = graph_commands.add_parser(
        "validate",
        help="Validate the live graph against the repository contract.",
    )
    graph_validate.set_defaults(function=_cmd_graph_validate)

    graph_stats_parser = graph_commands.add_parser(
        "stats",
        help="Show canonical graph record counts.",
    )
    graph_stats_parser.add_argument("--json", action="store_true")
    graph_stats_parser.set_defaults(function=_cmd_graph_stats)

    graph_export = graph_commands.add_parser(
        "export",
        help="Write a portable JSON snapshot (not an operational backup).",
    )
    graph_export.add_argument("--output")
    graph_export.set_defaults(function=_cmd_graph_export)

    new = commands.add_parser(
        "new",
        help="Create an optional YAML interchange record; Neo4j remains canonical.",
    )
    new.add_argument("record_type", choices=RECORD_CONFIG)
    new.add_argument("--name-slug")
    new.add_argument("--subject", help="Curator-supplied relationship subject.")
    new.add_argument("--object", help="Curator-supplied relationship object.")
    new.add_argument("--entity", help="Curator-supplied participation entity.")
    new.add_argument("--platform", help="Curator-supplied platform entity.")
    new.add_argument("--created-by", help="Curator identity to copy into creation metadata.")
    new.set_defaults(function=_cmd_new)

    reserve = commands.add_parser("reserve-id", help="Reserve and print the next ID.")
    reserve.add_argument("record_type", choices=RECORD_CONFIG)
    reserve.set_defaults(function=_cmd_reserve)

    validate = commands.add_parser(
        "validate",
        help="Validate optional YAML interchange records.",
    )
    validation_targets = validate.add_subparsers(dest="validation_target", required=True)
    validate_file_parser = validation_targets.add_parser("file")
    validate_file_parser.add_argument("path")
    validate_changed = validation_targets.add_parser("changed")
    validate_changed.add_argument("--base", default="origin/main")
    validate_registry_parser = validation_targets.add_parser("registry")
    validate_registry_parser.add_argument("--release-policy", action="store_true")
    validate.set_defaults(function=_cmd_validate)

    duplicates = commands.add_parser("find-duplicates", help="Report possible duplicate entities.")
    duplicates.add_argument("--threshold", type=float, default=0.86)
    duplicates.add_argument("--json", action="store_true")
    duplicates.set_defaults(function=_cmd_duplicates)

    review = commands.add_parser("review", help="Generate read-only curator review output.")
    review_targets = review.add_subparsers(dest="review_target", required=True)
    review_record = review_targets.add_parser("record")
    review_record.add_argument("identifier")
    review_changed = review_targets.add_parser("changed")
    review_changed.add_argument("--base", default="origin/main")
    review_targets.add_parser("registry")
    review.set_defaults(function=_cmd_review)

    build = commands.add_parser(
        "build",
        help="Build a bundle from optional YAML interchange records.",
    )
    build.add_argument("--output")
    build.add_argument("--skip-schema-artifacts", action="store_true")
    build.set_defaults(function=_cmd_build)

    generate = commands.add_parser("generate-schema", help="Generate LinkML artifacts.")
    generate.add_argument("--output")
    generate.set_defaults(function=_cmd_generate_schema)

    release = commands.add_parser("release", help="Prepare or verify a release.")
    release_commands = release.add_subparsers(dest="release_command", required=True)
    prepare = release_commands.add_parser("prepare")
    prepare.add_argument("--version", required=True)
    prepare.add_argument("--output")
    prepare.add_argument("--allow-dirty", action="store_true")
    prepare.set_defaults(function=_cmd_release_prepare)
    verify = release_commands.add_parser("verify")
    verify.add_argument("path")
    verify.set_defaults(function=_cmd_release_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except (
        GenerationError,
        IdentifierError,
        ReleaseError,
        RuntimeError,
        ScaffoldingError,
        ValueError,
    ) as error:
        print(f"phner: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
