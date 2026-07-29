"""Command-line interface for the PHNER Neo4j graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import project_root
from .neo4j_store import (
    GraphStoreError,
    Neo4jSettings,
    apply_migrations,
    check_connectivity,
    create_entity,
    create_relationship,
    export_graph,
    graph_stats,
    validate_graph,
)


def _root(args: argparse.Namespace) -> Path:
    return project_root(Path(args.project_root) if args.project_root else None)


def _graph_settings() -> Neo4jSettings:
    return Neo4jSettings.from_env()


def _cmd_graph_check(args: argparse.Namespace) -> int:
    information = check_connectivity(
        _graph_settings(),
        wait_seconds=args.wait_seconds,
    )
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
            f"{finding.identifier}: {finding.severity.upper()} [{finding.code}] {finding.message}"
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
        Path(args.output).resolve() if args.output else root / "build" / "neo4j-snapshot.json"
    )
    print(export_graph(_graph_settings(), destination))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phner", description=__doc__)
    parser.add_argument("--project-root", help="Override the PHNER repository root.")
    commands = parser.add_subparsers(dest="command", required=True)

    graph = commands.add_parser("graph", help="Manage the Neo4j graph.")
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
    graph_new_relationship.add_argument(
        "--type",
        dest="relationship_type",
        required=True,
    )
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
        help="Show graph record counts.",
    )
    graph_stats_parser.add_argument("--json", action="store_true")
    graph_stats_parser.set_defaults(function=_cmd_graph_stats)

    graph_export = graph_commands.add_parser(
        "export",
        help="Write a portable JSON snapshot (not an operational backup).",
    )
    graph_export.add_argument("--output")
    graph_export.set_defaults(function=_cmd_graph_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except (GraphStoreError, OSError, ValueError) as error:
        print(f"phner: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
