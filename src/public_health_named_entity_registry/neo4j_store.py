"""Neo4j-first storage, validation, and export operations."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

from neo4j import GraphDatabase, ManagedTransaction

from .config import project_root
from .yaml_io import load_yaml

SAFE_GRAPH_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENTITY_ID_PATTERN = re.compile(r"^phner-ent-[0-9]{6}$")
RELATIONSHIP_ID_PATTERN = re.compile(r"^phner-rel-[0-9]{6}$")
SYSTEM_RELATIONSHIP_TYPES = {
    "HAS_PLATFORM_PARTICIPATION",
    "SUPPORTED_BY",
    "WITH_PLATFORM",
}


class GraphStoreError(RuntimeError):
    """A user-actionable Neo4j graph operation error."""


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection settings sourced from environment variables."""

    uri: str
    username: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> Neo4jSettings:
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            raise GraphStoreError(
                "NEO4J_PASSWORD is required. Set it in your shell; do not commit it."
            )
        return cls(
            uri=os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
            username=os.environ.get("NEO4J_USERNAME", "neo4j"),
            password=password,
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )


@dataclass(frozen=True)
class GraphContract:
    """Repository-controlled labels and relationship vocabulary."""

    entity_labels: dict[str, str]
    relationship_types: tuple[str, ...]
    system_relationship_types: tuple[str, ...]


@dataclass(frozen=True)
class GraphFinding:
    """A validation finding from the live graph."""

    severity: str
    code: str
    identifier: str
    message: str


def load_graph_contract(root: Path | None = None) -> GraphContract:
    """Load and validate the graph vocabulary kept in Git."""

    root = project_root(root)
    mapping_raw = load_yaml(root / "mappings" / "neo4j_mapping.yaml")
    rules_raw = load_yaml(root / "mappings" / "relationship_rules.yaml")
    if not isinstance(mapping_raw, dict) or not isinstance(rules_raw, dict):
        raise GraphStoreError("Neo4j mapping and relationship rules must be YAML mappings.")
    labels_raw = mapping_raw.get("entity_labels")
    if not isinstance(labels_raw, dict) or not labels_raw:
        raise GraphStoreError("mappings/neo4j_mapping.yaml must define entity_labels.")
    labels = {str(key): str(value) for key, value in labels_raw.items()}
    system_types_raw = mapping_raw.get(
        "system_relationship_types",
        sorted(SYSTEM_RELATIONSHIP_TYPES),
    )
    if not isinstance(system_types_raw, list):
        raise GraphStoreError("system_relationship_types must be a YAML list.")
    system_types = tuple(sorted(str(value) for value in system_types_raw))
    relationship_types = tuple(sorted(str(key) for key in rules_raw))
    symbols = [*labels.values(), *relationship_types, *system_types]
    invalid = sorted(symbol for symbol in symbols if SAFE_GRAPH_SYMBOL.fullmatch(symbol) is None)
    if invalid:
        raise GraphStoreError(f"Unsafe Neo4j label or relationship type: {invalid[0]}")
    return GraphContract(labels, relationship_types, system_types)


def split_cypher_statements(text: str) -> list[str]:
    """Split repository migration files containing simple semicolon-delimited Cypher."""

    without_comments = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )
    return [statement.strip() for statement in without_comments.split(";") if statement.strip()]


def _driver(settings: Neo4jSettings) -> Any:
    return GraphDatabase.driver(
        settings.uri,
        auth=(settings.username, settings.password),
    )


def check_connectivity(
    settings: Neo4jSettings,
    *,
    wait_seconds: int = 0,
) -> dict[str, str]:
    """Verify connectivity, optionally waiting for a starting local database."""

    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with _driver(settings) as driver:
                driver.verify_connectivity()
                info = driver.get_server_info()
                return {
                    "address": str(info.address),
                    "agent": str(info.agent),
                    "database": settings.database,
                }
        except AuthError as error:
            raise GraphStoreError(f"Neo4j authentication failed: {error}") from error
        except (ServiceUnavailable, OSError) as error:
            if time.monotonic() >= deadline:
                raise GraphStoreError(
                    f"Cannot connect to Neo4j at {settings.uri}: {error}"
                ) from error
            time.sleep(1)


def apply_migrations(
    settings: Neo4jSettings,
    root: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Apply each repository migration exactly once to the selected database."""

    root = project_root(root)
    migration_paths = sorted((root / "neo4j" / "migrations").glob("*.cypher"))
    if not migration_paths:
        raise GraphStoreError("No Neo4j migrations found under neo4j/migrations.")
    applied: list[str] = []
    skipped: list[str] = []
    try:
        with _driver(settings) as driver:
            driver.verify_connectivity()
            for path in migration_paths:
                existing = driver.execute_query(
                    "MATCH (m:PhnerMigration {name: $name}) RETURN m.name AS name",
                    name=path.name,
                    database_=settings.database,
                )
                if existing.records:
                    skipped.append(path.name)
                    continue
                statements = split_cypher_statements(path.read_text(encoding="utf-8"))
                if not statements:
                    raise GraphStoreError(f"Migration contains no Cypher statements: {path}")
                for statement in statements:
                    driver.execute_query(statement, database_=settings.database)
                driver.execute_query(
                    """
                    MERGE (m:PhnerMigration {name: $name})
                    ON CREATE SET m.applied_at = datetime()
                    """,
                    name=path.name,
                    database_=settings.database,
                )
                applied.append(path.name)
    except Neo4jError as error:
        raise GraphStoreError(f"Neo4j migration failed: {error}") from error
    return applied, skipped


def _allocate_identifier(transaction: ManagedTransaction, kind: str, prefix: str) -> str:
    record = transaction.run(
        """
        MERGE (counter:PhnerCounter {kind: $kind})
        ON CREATE SET counter.value = 0
        SET counter.value = counter.value + 1
        RETURN counter.value AS sequence
        """,
        kind=kind,
    ).single(strict=True)
    sequence = int(record["sequence"])
    if sequence > 999_999:
        raise GraphStoreError(f"PHNER {kind} identifier space is exhausted.")
    return f"{prefix}{sequence:06d}"


def create_entity(
    settings: Neo4jSettings,
    preferred_name: str,
    entity_type: str,
    *,
    created_by: str | None = None,
    root: Path | None = None,
) -> str:
    """Create a minimally valid entity directly in the canonical graph."""

    name = preferred_name.strip()
    if not name:
        raise GraphStoreError("preferred_name cannot be blank.")
    contract = load_graph_contract(root)
    label = contract.entity_labels.get(entity_type)
    if label is None:
        allowed = ", ".join(sorted(contract.entity_labels))
        raise GraphStoreError(f"Unknown entity type {entity_type!r}; choose one of: {allowed}")

    def create(transaction: ManagedTransaction) -> str:
        identifier = _allocate_identifier(transaction, "entity", "phner-ent-")
        result = transaction.run(
            f"""
            CREATE (entity:NamedEntity:{label} {{
                entity_id: $entity_id,
                entity_type: $entity_type,
                preferred_name: $preferred_name,
                status: 'active',
                assertion_status: 'provisional',
                created_at: datetime(),
                created_by: $created_by
            }})
            RETURN entity.entity_id AS entity_id
            """,
            entity_id=identifier,
            entity_type=entity_type,
            preferred_name=name,
            created_by=created_by,
        ).single(strict=True)
        return str(result["entity_id"])

    try:
        with (
            _driver(settings) as driver,
            driver.session(database=settings.database) as session,
        ):
            return str(session.execute_write(create))
    except Neo4jError as error:
        raise GraphStoreError(f"Could not create entity: {error}") from error


def create_relationship(
    settings: Neo4jSettings,
    subject_entity_id: str,
    relationship_type: str,
    object_entity_id: str,
    *,
    created_by: str | None = None,
    root: Path | None = None,
) -> str:
    """Create an identified domain relationship between existing entities."""

    if ENTITY_ID_PATTERN.fullmatch(subject_entity_id) is None:
        raise GraphStoreError(f"Invalid subject entity ID: {subject_entity_id}")
    if ENTITY_ID_PATTERN.fullmatch(object_entity_id) is None:
        raise GraphStoreError(f"Invalid object entity ID: {object_entity_id}")
    contract = load_graph_contract(root)
    if relationship_type not in contract.relationship_types:
        allowed = ", ".join(contract.relationship_types)
        raise GraphStoreError(
            f"Unknown relationship type {relationship_type!r}; choose one of: {allowed}"
        )

    def create(transaction: ManagedTransaction) -> str:
        endpoints = transaction.run(
            """
            MATCH (subject:NamedEntity {entity_id: $subject})
            MATCH (object:NamedEntity {entity_id: $object})
            RETURN subject.entity_id AS subject, object.entity_id AS object
            """,
            subject=subject_entity_id,
            object=object_entity_id,
        ).single()
        if endpoints is None:
            raise GraphStoreError(
                "Both relationship endpoints must exist as NamedEntity nodes."
            )
        identifier = _allocate_identifier(transaction, "relationship", "phner-rel-")
        result = transaction.run(
            f"""
            MATCH (subject:NamedEntity {{entity_id: $subject}})
            MATCH (object:NamedEntity {{entity_id: $object}})
            CREATE (subject)-[relationship:{relationship_type} {{
                relationship_id: $relationship_id,
                assertion_status: 'provisional',
                created_at: datetime(),
                created_by: $created_by
            }}]->(object)
            RETURN relationship.relationship_id AS relationship_id
            """,
            subject=subject_entity_id,
            object=object_entity_id,
            relationship_id=identifier,
            created_by=created_by,
        ).single(strict=True)
        return str(result["relationship_id"])

    try:
        with (
            _driver(settings) as driver,
            driver.session(database=settings.database) as session,
        ):
            return str(session.execute_write(create))
    except GraphStoreError:
        raise
    except Neo4jError as error:
        raise GraphStoreError(f"Could not create relationship: {error}") from error


def graph_stats(settings: Neo4jSettings) -> dict[str, int]:
    """Return small operational counts for the PHNER graph."""

    queries = {
        "entities": "MATCH (n:NamedEntity) RETURN count(n) AS count",
        "relationships": (
            "MATCH (:NamedEntity)-[r]->(:NamedEntity) "
            "WHERE r.relationship_id IS NOT NULL RETURN count(r) AS count"
        ),
        "evidence_sources": "MATCH (n:EvidenceSource) RETURN count(n) AS count",
        "participations": "MATCH (n:PlatformParticipation) RETURN count(n) AS count",
    }
    try:
        with _driver(settings) as driver:
            driver.verify_connectivity()
            return {
                key: int(
                    driver.execute_query(query, database_=settings.database).records[0]["count"]
                )
                for key, query in queries.items()
            }
    except Neo4jError as error:
        raise GraphStoreError(f"Could not read graph statistics: {error}") from error


def validate_graph(
    settings: Neo4jSettings,
    root: Path | None = None,
) -> list[GraphFinding]:
    """Run baseline graph-contract checks against the live database."""

    contract = load_graph_contract(root)
    allowed_relationship_types = [
        *contract.relationship_types,
        *contract.system_relationship_types,
    ]
    checks: list[tuple[str, str, str, str, dict[str, Any]]] = [
        (
            "error",
            "missing-entity-id",
            "NamedEntity is missing entity_id.",
            """
            MATCH (n:NamedEntity)
            WHERE n.entity_id IS NULL
            RETURN elementId(n) AS identifier
            """,
            {},
        ),
        (
            "error",
            "invalid-entity-id",
            "NamedEntity has an invalid PHNER entity ID.",
            """
            MATCH (n:NamedEntity)
            WHERE n.entity_id IS NOT NULL
              AND NOT (n.entity_id =~ '^phner-ent-[0-9]{6}$')
            RETURN toString(n.entity_id) AS identifier
            """,
            {},
        ),
        (
            "error",
            "blank-preferred-name",
            "NamedEntity is missing a non-blank preferred_name.",
            """
            MATCH (n:NamedEntity)
            WHERE n.preferred_name IS NULL OR trim(toString(n.preferred_name)) = ''
            RETURN coalesce(n.entity_id, elementId(n)) AS identifier
            """,
            {},
        ),
        (
            "error",
            "unknown-entity-type",
            "NamedEntity has an entity_type outside the graph contract.",
            """
            MATCH (n:NamedEntity)
            WHERE n.entity_type IS NULL OR NOT (n.entity_type IN $entity_types)
            RETURN coalesce(n.entity_id, elementId(n)) AS identifier
            """,
            {"entity_types": sorted(contract.entity_labels)},
        ),
        (
            "error",
            "missing-relationship-id",
            "Domain relationship is missing relationship_id.",
            """
            MATCH ()-[r]->()
            WHERE type(r) IN $relationship_types AND r.relationship_id IS NULL
            RETURN elementId(r) AS identifier
            """,
            {"relationship_types": list(contract.relationship_types)},
        ),
        (
            "error",
            "invalid-relationship-id",
            "Domain relationship has an invalid PHNER relationship ID.",
            """
            MATCH ()-[r]->()
            WHERE type(r) IN $relationship_types
              AND r.relationship_id IS NOT NULL
              AND NOT (r.relationship_id =~ '^phner-rel-[0-9]{6}$')
            RETURN toString(r.relationship_id) AS identifier
            """,
            {"relationship_types": list(contract.relationship_types)},
        ),
        (
            "error",
            "duplicate-relationship-id",
            "Multiple relationships share the same relationship_id.",
            """
            MATCH ()-[r]->()
            WHERE r.relationship_id IS NOT NULL
            WITH r.relationship_id AS identifier, count(*) AS occurrences
            WHERE occurrences > 1
            RETURN toString(identifier) AS identifier
            """,
            {},
        ),
        (
            "error",
            "invalid-relationship-endpoint",
            "Domain relationship endpoints must both be NamedEntity nodes.",
            """
            MATCH (subject)-[r]->(object)
            WHERE type(r) IN $relationship_types
              AND (NOT (subject:NamedEntity) OR NOT (object:NamedEntity))
            RETURN coalesce(r.relationship_id, elementId(r)) AS identifier
            """,
            {"relationship_types": list(contract.relationship_types)},
        ),
        (
            "warning",
            "unknown-relationship-type",
            "Relationship type is outside the PHNER graph contract.",
            """
            MATCH ()-[r]->()
            WHERE NOT (type(r) IN $allowed_relationship_types)
            RETURN coalesce(r.relationship_id, elementId(r)) AS identifier
            """,
            {"allowed_relationship_types": allowed_relationship_types},
        ),
    ]
    findings: list[GraphFinding] = []
    try:
        with _driver(settings) as driver:
            driver.verify_connectivity()
            for severity, code, message, query, parameters in checks:
                result = driver.execute_query(
                    query,
                    parameters_=parameters,
                    database_=settings.database,
                )
                findings.extend(
                    GraphFinding(severity, code, str(record["identifier"]), message)
                    for record in result.records
                )
    except Neo4jError as error:
        raise GraphStoreError(f"Could not validate graph: {error}") from error
    return sorted(
        findings,
        key=lambda finding: (finding.severity, finding.code, finding.identifier),
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (dt.date, dt.datetime, dt.time)):
        return value.isoformat()
    iso_format = getattr(value, "iso_format", None)
    if callable(iso_format):
        return str(iso_format())
    return value


def export_graph(
    settings: Neo4jSettings,
    destination: Path,
) -> Path:
    """Export a portable, reviewable JSON snapshot; this is not an operational backup."""

    try:
        with _driver(settings) as driver:
            driver.verify_connectivity()
            node_result = driver.execute_query(
                """
                MATCH (node)
                WHERE node:NamedEntity
                   OR node:EvidenceSource
                   OR node:PlatformParticipation
                RETURN labels(node) AS labels, properties(node) AS properties
                ORDER BY coalesce(
                    node.entity_id,
                    node.source_id,
                    node.participation_id,
                    elementId(node)
                )
                """,
                database_=settings.database,
            )
            relationship_result = driver.execute_query(
                """
                MATCH (source)-[relationship]->(target)
                WHERE (source:NamedEntity OR source:EvidenceSource
                       OR source:PlatformParticipation)
                  AND (target:NamedEntity OR target:EvidenceSource
                       OR target:PlatformParticipation)
                RETURN
                    coalesce(
                        source.entity_id,
                        source.source_id,
                        source.participation_id,
                        elementId(source)
                    ) AS source,
                    type(relationship) AS type,
                    properties(relationship) AS properties,
                    coalesce(
                        target.entity_id,
                        target.source_id,
                        target.participation_id,
                        elementId(target)
                    ) AS target
                ORDER BY source, type, target
                """,
                database_=settings.database,
            )
    except Neo4jError as error:
        raise GraphStoreError(f"Could not export graph: {error}") from error
    snapshot = {
        "exported_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "database": settings.database,
        "nodes": [record.data() for record in node_result.records],
        "relationships": [record.data() for record in relationship_result.records],
    }
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(_json_ready(snapshot), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination
