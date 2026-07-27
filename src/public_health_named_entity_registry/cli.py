"""Command-line interface for PHNER curation and release work."""

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

    new = commands.add_parser("new", help="Reserve an ID and create a blank curator record.")
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

    validate = commands.add_parser("validate", help="Validate a file, changed files, or registry.")
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

    build = commands.add_parser("build", help="Build a development bundle.")
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
