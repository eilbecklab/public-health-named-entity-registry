from __future__ import annotations

from pathlib import Path

import pytest

from public_health_named_entity_registry.cli import build_parser
from public_health_named_entity_registry.neo4j_store import (
    GraphStoreError,
    Neo4jSettings,
    load_graph_contract,
    split_cypher_statements,
)


def test_neo4j_settings_require_password(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    with pytest.raises(GraphStoreError, match="NEO4J_PASSWORD"):
        Neo4jSettings.from_env()


def test_neo4j_settings_have_local_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "synthetic-test-password")
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_DATABASE", raising=False)
    settings = Neo4jSettings.from_env()
    assert settings.uri == "neo4j://localhost:7687"
    assert settings.username == "neo4j"
    assert settings.database == "neo4j"


def test_graph_contract_loads_repository_vocabularies(repository_root: Path):
    contract = load_graph_contract(repository_root)
    assert contract.entity_labels["organization"] == "Organization"
    assert "PART_OF" in contract.relationship_types
    assert "SAME_AS" in contract.relationship_types
    assert "SUPPORTED_BY" in contract.system_relationship_types


def test_migration_statements_are_semicolon_delimited(repository_root: Path):
    migration = (
        repository_root / "neo4j" / "migrations" / "001_initial_graph_contract.cypher"
    )
    statements = split_cypher_statements(migration.read_text())
    assert len(statements) == 7
    assert all(not statement.startswith("//") for statement in statements)
    assert any("phner_entity_id_unique" in statement for statement in statements)


def test_graph_cli_parses_entity_creation():
    args = build_parser().parse_args(
        [
            "graph",
            "new-entity",
            "--name",
            "Synthetic Health Authority",
            "--type",
            "organization",
            "--created-by",
            "synthetic-test-suite",
        ]
    )
    assert args.graph_command == "new-entity"
    assert args.entity_type == "organization"
